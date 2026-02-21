import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(not os.environ.get("POSTGRES_DSN"), reason="POSTGRES_DSN is required for migration test")
def test_sqlite_to_postgres_migration_script(tmp_path: Path):
    sqlite_path = tmp_path / "migration_source.db"
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute("CREATE TABLE user (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password_hash TEXT NOT NULL)")
        conn.execute(
            "CREATE TABLE palette (id INTEGER PRIMARY KEY, name TEXT NOT NULL, colors TEXT NOT NULL, user_id INTEGER NOT NULL, created_at TEXT)"
        )
        conn.execute("INSERT INTO user (id, username, password_hash) VALUES (1, 'u1', 'hash')")
        conn.execute("INSERT INTO palette (id, name, colors, user_id, created_at) VALUES (1, 'p1', '[]', 1, '2026-02-21')")
        conn.commit()

    script = Path("deploy/scripts/migrate_sqlite_to_postgres.py")
    env = os.environ.copy()
    env["SQLITE_PATH"] = str(sqlite_path)

    result = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Migration completed successfully" in result.stdout
