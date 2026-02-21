# Продакшн-деплой Paleta (SQLite)

Эта инструкция запускает проект на одном VPS через Docker + Nginx + HTTPS, с постоянным хранением SQLite и ежедневными бэкапами.

## 1. Требования

- Ubuntu 22.04/24.04 на VPS
- Домен с `A`-записями на IP сервера (`@` и `www`)
- Docker + Docker Compose plugin
- Nginx + Certbot

## 2. Подготовка сервера

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx sqlite3
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
- `DATABASE_URL=sqlite:////app/instance/paleta.db`
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

## 4. Запуск контейнера

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Проверка health:

```bash
curl http://127.0.0.1:8000/healthz
```

Ожидается: `{"status":"ok"}`.

## 5. Настройка Nginx reverse proxy

Скопируйте шаблон и замените домен:

```bash
sudo cp deploy/nginx/paleta.conf /etc/nginx/sites-available/paleta
sudo nano /etc/nginx/sites-available/paleta
```

В файле замените `example.com` и `www.example.com` на ваш домен.

Активируйте конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/paleta /etc/nginx/sites-enabled/paleta
sudo nginx -t
sudo systemctl reload nginx
```

## 6. SSL (Let’s Encrypt)

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Проверьте автообновление:

```bash
sudo certbot renew --dry-run
```

## 7. Ежедневные бэкапы SQLite (14 дней хранения)

Сделайте скрипт исполняемым:

```bash
chmod +x deploy/scripts/backup_sqlite.sh
```

Протестируйте вручную:

```bash
PROJECT_DIR=/opt/paleta ./deploy/scripts/backup_sqlite.sh
ls -la /opt/paleta/backups/sqlite
```

Добавьте cron-задачу:

```bash
crontab deploy/cron/paleta-backup.cron
crontab -l
```

## 8. Smoke-тест после деплоя

1. Открыть `https://your-domain.com` с телефона и ноутбука.
2. Зарегистрировать пользователя, сохранить палитру.
3. Зайти в тот же аккаунт с другого устройства и проверить, что палитра на месте.
4. Перезапустить контейнер:
   ```bash
   docker compose -f docker-compose.prod.yml restart
   ```
5. Проверить, что данные и загрузки сохранились.
6. Проверить `https`, редирект с `http` и `/healthz`.

## 9. Полезные команды эксплуатации

Логи:

```bash
docker compose -f docker-compose.prod.yml logs -f app
```

Пересборка после обновления кода:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка на блокировки SQLite:

```bash
docker compose -f docker-compose.prod.yml logs app | grep -i "database is locked"
```
