# Продакшн-деплой Paleta (PostgreSQL)

Эта инструкция запускает Paleta на одном VPS через Docker + Nginx + HTTPS c PostgreSQL и ежедневными бэкапами.

## 1. Требования

- Ubuntu 22.04/24.04 на VPS
- Домен с `A`-записями на IP сервера (`@` и `www`)
- Docker + Docker Compose plugin
- Nginx + Certbot
- `postgresql-client` на хосте (для `pg_dump`)

## 2. Подготовка сервера

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx postgresql-client
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

Создайте prod-env:

```bash
cp .env.prod.example .env.prod
```

Сгенерируйте ключи и вставьте в `.env.prod`:

```bash
openssl rand -hex 32
openssl rand -hex 32
```

Проверьте ключевые переменные:

- `FLASK_ENV=production`
- `SECRET_KEY=<длинная случайная строка>`
- `JWT_SECRET_KEY=<отдельная длинная случайная строка>`
- `DATABASE_URL=postgresql+psycopg://paleta:<password>@postgres:5432/paleta`
- `AUTO_CREATE_TABLES=false`
- `SESSION_COOKIE_SECURE=true`
- `CORS_ENABLED=false`
- `JWT_ACCESS_TTL_MINUTES=15`
- `JWT_REFRESH_TTL_DAYS=30`

При необходимости задайте SMTP/SMS для восстановления пароля.

## 4. Запуск контейнеров

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

`app` автоматически выполняет `flask db upgrade` при старте.

Проверка health:

```bash
curl http://127.0.0.1:8000/healthz
```

Ожидается: `{"status":"ok"}`.

## 5. Настройка Nginx reverse proxy

```bash
sudo cp deploy/nginx/paleta.conf /etc/nginx/sites-available/paleta
sudo nano /etc/nginx/sites-available/paleta
```

Замените `example.com` / `www.example.com` на ваш домен.

```bash
sudo ln -s /etc/nginx/sites-available/paleta /etc/nginx/sites-enabled/paleta
sudo nginx -t
sudo systemctl reload nginx
```

## 6. SSL (Let’s Encrypt)

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo certbot renew --dry-run
```

## 7. Ежедневные бэкапы PostgreSQL

Сделайте скрипт исполняемым:

```bash
chmod +x deploy/scripts/backup_postgres.sh
```

Протестируйте вручную:

```bash
PROJECT_DIR=/opt/paleta ./deploy/scripts/backup_postgres.sh
ls -la /opt/paleta/backups/postgres
```

Подключите cron:

```bash
crontab deploy/cron/paleta-postgres-backup.cron
crontab -l
```

## 8. Миграция данных SQLite -> PostgreSQL

Если переносите существующий прод с SQLite:

1. Включите окно обслуживания.
2. Создайте backup SQLite-файла.
3. Запустите перенос:

```bash
POSTGRES_DSN="postgresql+psycopg://paleta:<password>@127.0.0.1:5432/paleta" \
SQLITE_PATH="/opt/paleta/data/instance/paleta.db" \
python3 deploy/scripts/migrate_sqlite_to_postgres.py
```

Скрипт проверяет row count parity по ключевым таблицам и завершится ошибкой при несовпадении.

## 9. Smoke-тест после деплоя

1. `GET /healthz` возвращает `200`.
2. Веб-логин работает.
3. Создание/редактирование/удаление палитры в вебе работает.
4. Mobile API работает:
   - `POST /api/v1/auth/login`
   - `GET /api/v1/palettes` (с Bearer token)

## 10. Полезные команды эксплуатации

Логи приложения:

```bash
docker compose -f docker-compose.prod.yml logs -f app
```

Логи PostgreSQL:

```bash
docker compose -f docker-compose.prod.yml logs -f postgres
```

Пересборка после обновления кода:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
