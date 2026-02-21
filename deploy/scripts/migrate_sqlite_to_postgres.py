#!/usr/bin/env python3
"""One-off data migration from SQLite to PostgreSQL with row-count verification."""

from __future__ import annotations

import os
import sqlite3
import sys
from dataclasses import dataclass

import psycopg
from psycopg import sql


TABLES_IN_ORDER = [
    "user",
    "user_contact",
    "password_reset_token",
    "palette",
    "upload",
    "refresh_tokens",
]


@dataclass
class Counts:
    sqlite_count: int
    pg_count: int


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_postgres_dsn(dsn: str) -> str:
    if dsn.startswith("postgresql+") and "://" in dsn:
        _, rest = dsn.split("://", 1)
        return f"postgresql://{rest}"
    return dsn


def get_table_names_sqlite(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def get_table_names_postgres(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        return {row[0] for row in cur.fetchall()}


def fetch_sqlite_rows(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    cursor = conn.execute(f'SELECT * FROM "{table}"')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def truncate_postgres_tables(conn: psycopg.Connection, tables: list[str]) -> None:
    with conn.cursor() as cur:
        for table in reversed(tables):
            cur.execute(
                sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(sql.Identifier(table))
            )


def insert_rows(conn: psycopg.Connection, table: str, columns: list[str], rows: list[tuple]) -> None:
    if not rows:
        return

    col_identifiers = sql.SQL(", ").join(sql.Identifier(col) for col in columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        col_identifiers,
        placeholders,
    )

    with conn.cursor() as cur:
        cur.executemany(statement, rows)


def reset_sequence(conn: psycopg.Connection, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        if not cur.fetchone()[0]:
            return

        cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
        sequence_name = cur.fetchone()[0]
        if not sequence_name:
            return

        cur.execute(sql.SQL("SELECT COALESCE(MAX(id), 0) FROM {}").format(sql.Identifier(table)))
        max_id = cur.fetchone()[0]
        if max_id > 0:
            cur.execute("SELECT setval(%s, %s, true)", (sequence_name, max_id))
        else:
            cur.execute("SELECT setval(%s, 1, false)", (sequence_name,))


def count_rows_sqlite(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def count_rows_postgres(conn: psycopg.Connection, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
        return cur.fetchone()[0]


def main() -> None:
    sqlite_path = os.environ.get("SQLITE_PATH", "data/instance/paleta.db")
    postgres_dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")

    if not os.path.exists(sqlite_path):
        fail(f"SQLite database not found: {sqlite_path}")
    if not postgres_dsn:
        fail("POSTGRES_DSN or DATABASE_URL must be provided")
    postgres_dsn = normalize_postgres_dsn(postgres_dsn)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        with psycopg.connect(postgres_dsn) as pg_conn:
            pg_conn.autocommit = False

            sqlite_tables = get_table_names_sqlite(sqlite_conn)
            pg_tables = get_table_names_postgres(pg_conn)
            tables_to_copy = [t for t in TABLES_IN_ORDER if t in sqlite_tables and t in pg_tables]

            if not tables_to_copy:
                fail("No matching tables found between SQLite and PostgreSQL")

            truncate_postgres_tables(pg_conn, tables_to_copy)

            for table in tables_to_copy:
                columns, rows = fetch_sqlite_rows(sqlite_conn, table)
                insert_rows(pg_conn, table, columns, rows)
                reset_sequence(pg_conn, table)

            counts: dict[str, Counts] = {}
            for table in tables_to_copy:
                sqlite_count = count_rows_sqlite(sqlite_conn, table)
                pg_count = count_rows_postgres(pg_conn, table)
                counts[table] = Counts(sqlite_count=sqlite_count, pg_count=pg_count)

            mismatches = [t for t, c in counts.items() if c.sqlite_count != c.pg_count]
            if mismatches:
                pg_conn.rollback()
                for table in mismatches:
                    c = counts[table]
                    print(
                        f"Mismatch in table '{table}': sqlite={c.sqlite_count}, postgres={c.pg_count}",
                        file=sys.stderr,
                    )
                fail("Row counts mismatch. Transaction rolled back.")

            pg_conn.commit()

            print("Migration completed successfully.")
            for table, c in counts.items():
                print(f"{table}: sqlite={c.sqlite_count}, postgres={c.pg_count}")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    main()
