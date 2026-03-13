# Продакшн-деплой Paleta (PostgreSQL)

Эта инструкция запускает проект на одном VPS через Docker + Nginx + HTTPS, с PostgreSQL и ежедневными бэкапами.

## 1. Требования

- Ubuntu 22.04/24.04 на VPS
- Домен с `A`-записями на IP сервера (`@` и `www`)
- Docker + Docker Compose plugin
- Nginx + Certbot
- `libnginx-mod-http-geoip2` + база GeoLite2 Country (для шаблона `deploy/nginx/paleta.conf`)

## 2. Подготовка сервера

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx libnginx-mod-http-geoip2
```

Установите Docker (официальным способом) и проверьте:

```bash
docker --version
docker compose version
```

## 3. Клонирование и конфиг приложения

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> paleta
sudo chown -R $USER:$USER /opt/paleta
cd /opt/paleta
```

Создайте прод-env:

```bash
cp .env.prod.example .env.prod
```

Сгенерируйте секрет и вставьте в `.env.prod`:

```bash
openssl rand -hex 32
```

Проверьте, что в `.env.prod`:

- `FLASK_ENV=production`
- `SECRET_KEY=<длинная случайная строка>`
- `POSTGRES_DB=paleta`
- `POSTGRES_USER=paleta`
- `POSTGRES_PASSWORD=<сильный пароль>`
- `DATABASE_URL=postgresql+psycopg://paleta:<сильный пароль>@db:5432/paleta`
- `SESSION_COOKIE_SECURE=true`
- `CORS_ENABLED=false`
- `MAX_IMAGE_PIXELS=20000000`
- `PASSWORD_RESET_CODE_TTL_MINUTES=15`
- `PASSWORD_RESET_MAX_ATTEMPTS=5`

Если хотите восстановление через email, задайте SMTP:

- `SMTP_HOST=...`
- `SMTP_PORT=587`
- `SMTP_USER=...`
- `SMTP_PASSWORD=...`
- `SMTP_FROM=...`

## 4. Миграция данных из SQLite в PostgreSQL

Этот шаг нужен только если у вас уже есть данные в `data/instance/paleta.db`.

1. Сохраните резервную копию старой SQLite-базы:

```bash
mkdir -p backups/sqlite
cp data/instance/paleta.db "backups/sqlite/paleta_before_pg_$(date -u +'%Y%m%d_%H%M%S').db"
```

2. Соберите контейнер приложения и запустите только PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml up -d --build db
```

3. Создайте таблицы в PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml run --rm app python -c "from app import app; from extensions import db; import models; app.app_context().push(); db.create_all()"
```

4. Перенесите данные (без создания отдельных файлов):

```bash
docker compose -f docker-compose.prod.yml run --rm app python - <<'PY'
import json
import os
from pathlib import Path

from sqlalchemy import MetaData, create_engine, select, text

sqlite_path = os.environ.get("SQLITE_PATH", "/app/instance/paleta.db")
if not Path(sqlite_path).exists():
    raise SystemExit(f"SQLite file not found: {sqlite_path}")

source_engine = create_engine(f"sqlite:///{sqlite_path}")
target_engine = create_engine(os.environ["DATABASE_URL"])

tables = ["user", "user_contact", "upload", "palette", "password_reset_token"]

source_meta = MetaData()
target_meta = MetaData()
source_meta.reflect(bind=source_engine)
target_meta.reflect(bind=target_engine)

existing_tables = [name for name in tables if name in source_meta.tables and name in target_meta.tables]
if not existing_tables:
    raise SystemExit("No matching tables found for migration.")

delete_order = [name for name in ["password_reset_token", "palette", "upload", "user_contact", "user"] if name in existing_tables]

with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
    for table_name in delete_order:
        target_conn.execute(target_meta.tables[table_name].delete())

    for table_name in existing_tables:
        rows = source_conn.execute(select(source_meta.tables[table_name])).mappings().all()
        payload = []
        for row in rows:
            item = dict(row)
            if table_name == "palette" and isinstance(item.get("colors"), str):
                item["colors"] = json.loads(item["colors"])
            payload.append(item)
        if payload:
            target_conn.execute(target_meta.tables[table_name].insert(), payload)

    for table_name in existing_tables:
        query = (
            "SELECT setval(pg_get_serial_sequence('\"{0}\"', 'id'), "
            "COALESCE((SELECT MAX(id) FROM \"{0}\"), 1), true)"
        ).format(table_name)
        target_conn.execute(text(query))

print("SQLite -> PostgreSQL migration finished.")
PY
```

5. Запустите приложение:

```bash
docker compose -f docker-compose.prod.yml up -d app
```

## 5. Запуск контейнеров (чистая установка)

Если перенос из SQLite не требуется, достаточно:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Проверка health:

```bash
curl http://127.0.0.1:8000/healthz
```

Ожидается: `{"status":"ok"}`.

## 6. Настройка Nginx reverse proxy

Скопируйте шаблон и замените домен:

```bash
sudo cp deploy/nginx/paleta.conf /etc/nginx/sites-available/paleta
sudo nano /etc/nginx/sites-available/paleta
```

В файле замените `example.com` и `www.example.com` на ваш домен.

Важно по GeoIP2:
- Шаблон `deploy/nginx/paleta.conf` использует директиву `geoip2` и файл `/etc/nginx/GeoLite2-Country.mmdb`.
- Если модуль/база не установлены, закомментируйте блок `geoip2 ...` и строку `proxy_set_header X-Country-Code $geoip2_country_code;`, затем проверьте `sudo nginx -t`.

Активируйте конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/paleta /etc/nginx/sites-enabled/paleta
sudo nginx -t
sudo systemctl reload nginx
```

## 7. SSL (Let’s Encrypt)

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Проверьте автообновление:

```bash
sudo certbot renew --dry-run
```

## 8. Ежедневные бэкапы PostgreSQL (14 дней хранения)

Сделайте скрипт исполняемым:

```bash
chmod +x deploy/scripts/backup_postgres.sh
```

Протестируйте вручную:

```bash
PROJECT_DIR=/opt/paleta ./deploy/scripts/backup_postgres.sh
ls -la /opt/paleta/backups/postgres
```

Добавьте cron-задачу:

```bash
crontab deploy/cron/paleta-backup.cron
crontab -l
```

## 9. Smoke-тест после деплоя

1. Открыть `https://your-domain.com` с телефона и ноутбука.
2. Зарегистрировать пользователя, сохранить палитру.
3. Зайти в тот же аккаунт с другого устройства и проверить, что палитра на месте.
4. Перезапустить контейнер:
   ```bash
   docker compose -f docker-compose.prod.yml restart
   ```
5. Проверить, что данные и загрузки сохранились.
6. Проверить `https`, редирект с `http` и `/healthz`.

## 10. Полезные команды эксплуатации

Логи:

```bash
docker compose -f docker-compose.prod.yml logs -f app
docker compose -f docker-compose.prod.yml logs -f db
```

Пересборка после обновления кода:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка соединения с PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT NOW();"'
```
