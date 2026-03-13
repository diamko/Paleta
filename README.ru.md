# Paleta

<p align="right">
  🌍  <strong>Язык:</strong>
  🇬🇧  <a href="README.md">English</a> |
  🇷🇺  Русский
</p>

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-black.svg)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#)

<p align="center">
  <a href="https://diamko.ru">
    <img src="https://img.shields.io/badge/Website-diamko.ru-ff6a00?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Сайт diamko.ru">
  </a>
</p>

<p align="center">
  <strong>Мой сайт:</strong> <a href="https://diamko.ru">diamko.ru</a>
</p>

Paleta - это веб-приложение для генерации, редактирования, сохранения и экспорта цветовых палитр.
Вы можете создавать палитры из загруженных изображений (извлечение доминирующих цветов через KMeans) или генерировать случайные палитры, а затем управлять ими в личном аккаунте.

Проект ориентирован на дизайнеров, frontend-разработчиков и всех, кто работает с цветом и хочет быстро переходить от изображения к готовым HEX-кодам.

Гайд по продакшн-деплою (PostgreSQL + Docker + Nginx + HTTPS): `DEPLOYMENT.ru.md`.

<a id="toc-ru"></a>

## Оглавление

1. [Зачем создан Paleta](#why-ru)
2. [Ключевые функции](#features-ru)
3. [Технологии](#stack-ru)
4. [Как это работает](#workflow-ru)
5. [Установка и настройка](#install-ru)
6. [Запуск проекта](#run-ru)
7. [Конфигурация](#config-ru)
8. [Как пользоваться](#usage-ru)
9. [API-эндпоинты](#api-ru)
10. [Структура проекта](#structure-ru)
11. [Тестирование](#tests-ru)
12. [Roadmap](#roadmap-ru)
13. [Как внести вклад](#contrib-ru)
14. [Автор](#author-ru)
15. [Лицензия](#license-ru)

<a id="why-ru"></a>

## Зачем создан Paleta

### Цель

Сделать удобный браузерный инструмент, который превращает визуальные референсы в готовые цветовые палитры.

### Какую проблему решает проект

- Ручной подбор цветов с изображений занимает много времени.
- Экспорт палитр в форматы дизайн-инструментов часто требует сторонних утилит.
- Без аккаунта и базы данных сложно хранить и систематизировать большое количество палитр.

### Что было изучено при разработке

- Построение модульной архитектуры Flask-приложения.
- Интеграция обработки изображений и кластеризации цветов (Pillow + NumPy + scikit-learn KMeans).
- Реализация аутентификации и хранения данных пользователей через Flask-Login + SQLAlchemy.
- Поддержка экспорта палитр в несколько форматов: JSON, GPL, ASE, CSV, PNG, ACO.

### Чем проект отличается

- Два режима генерации: по изображению и случайная палитра.
- Встроенное редактирование цветов (color picker + HEX + копирование).
- Управление палитрами в аккаунте (сохранение, переименование, удаление, фильтры, сортировка).
- Экспорт в форматы, которые подходят и разработчикам, и дизайнерам.

<a id="features-ru"></a>

## Ключевые функции

- Загрузка изображений через drag-and-drop или кнопку выбора файла.
- Извлечение доминирующих цветов из изображения с помощью KMeans.
- Генерация случайных палитр.
- Редактирование палитры (HEX + color picker), пересчет с другим количеством цветов.
- Экспорт в форматы: `JSON`, `GPL`, `ASE`, `CSV`, `PNG`, `ACO`.
- Аутентификация пользователей (регистрация, вход, выход).
- Личная библиотека палитр с поиском, фильтрами и сортировкой.
- Раздел недавних изображений (за последние 7 дней) для авторизованных пользователей.
- Автоматическая очистка старых загрузок при старте приложения.

<a id="stack-ru"></a>

## Технологии

- `Python 3.12`
- `Flask 2.3.3`
- `Flask-SQLAlchemy`
- `Flask-Login`
- `Flask-CORS`
- `Pillow`
- `NumPy`
- `scikit-learn` (KMeans)
- `PostgreSQL` (база данных по умолчанию)
- `Bootstrap 5` + Vanilla JavaScript

<a id="workflow-ru"></a>

## Как это работает

1. Пользователь загружает изображение.
2. Бэкенд уменьшает изображение и запускает кластеризацию KMeans.
3. Доминирующие RGB-цвета преобразуются в HEX.
4. Пользователь может редактировать, копировать, экспортировать или сохранить палитру.
5. Сохраненные палитры привязываются к аккаунту и доступны в разделе "Мои палитры".

<a id="install-ru"></a>

## Установка и настройка

### Требования

- `git`
- `Python 3.10+` (рекомендуется `3.12`)
- `pip`
- `PostgreSQL` (или Docker для запуска PostgreSQL-контейнера)

### 1) Клонирование репозитория

```bash
git clone <your-repo-url>
cd Paleta
```

### 2) Создание и активация виртуального окружения

Важно:
- используйте `.venv` (с точкой в начале), а не `venv`;
- на Windows используйте команды `python`, а не `python3`.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Инициализация базы данных (первый запуск)

Быстрый запуск локального PostgreSQL через Docker:

```bash
docker run --name paleta-postgres \
  -e POSTGRES_DB=paleta \
  -e POSTGRES_USER=paleta \
  -e POSTGRES_PASSWORD=paleta \
  -p 5432:5432 \
  -d postgres:latest
```

Linux/macOS:

```bash
python3 -c "from app import app; from extensions import db; import models; app.app_context().push(); db.create_all()"
```

Windows (PowerShell):

```powershell
python -c "from app import app; from extensions import db; import models; app.app_context().push(); db.create_all()"
```

По умолчанию приложение ожидает PostgreSQL:

- development: `postgresql+psycopg://paleta:paleta@localhost:5432/paleta`
- production: `postgresql+psycopg://paleta:paleta@db:5432/paleta`

<a id="run-ru"></a>

## Запуск проекта

### Вариант A: прямой запуск

Linux/macOS:

```bash
python3 app.py
```

Windows (PowerShell):

```powershell
python app.py
```

### Вариант B: Flask CLI

```bash
flask --app app run
```

Откройте в браузере: `http://127.0.0.1:5000`

<a id="config-ru"></a>

## Конфигурация

Основные параметры находятся в `config.py`.

### Переменные окружения

- `SECRET_KEY` (обязательная в `production`, опциональна для локальной разработки)
- `DATABASE_URL` (опционально; по умолчанию локальная PostgreSQL в development и PostgreSQL-контейнер `db` в production)
- `FLASK_ENV` (`production` для продакшна)
- `SESSION_COOKIE_SECURE` (`true` по умолчанию в production, `false` в development)
- `CORS_ENABLED` (`false` по умолчанию; включайте только если API вызывается с другого origin)
- `CORS_ORIGINS` (список разрешённых origin через запятую, если `CORS_ENABLED=true`)
- `MAX_IMAGE_PIXELS` (максимальное разрешение изображения в пикселях; по умолчанию `20000000`)
- `MIN_COLOR_COUNT`, `MAX_COLOR_COUNT` (границы количества цветов при генерации и валидации палитры; по умолчанию `3` и `15`)
- `PASSWORD_RESET_CODE_TTL_MINUTES` (время жизни кода восстановления в минутах; по умолчанию `15`)
- `PASSWORD_RESET_MAX_ATTEMPTS` (макс. число попыток ввода кода; по умолчанию `5`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` (отправка кода по email)
- `SMTP_USE_TLS`, `SMTP_USE_SSL` (режимы защиты SMTP)

Пример (Linux/macOS):

```bash
export SECRET_KEY="replace-with-a-secure-random-value"
export DATABASE_URL="postgresql+psycopg://paleta:paleta@localhost:5432/paleta"
export FLASK_ENV="development"
export SESSION_COOKIE_SECURE="false"
export CORS_ENABLED="false"
export MAX_IMAGE_PIXELS="20000000"
export PASSWORD_RESET_CODE_TTL_MINUTES="15"
export PASSWORD_RESET_MAX_ATTEMPTS="5"
```

### Параметры по умолчанию

- `SQLALCHEMY_DATABASE_URI` берется из `DATABASE_URL`
- URL БД по умолчанию (если не задан):
  - development: `postgresql+psycopg://paleta:paleta@localhost:5432/paleta`
  - production: `postgresql+psycopg://paleta:paleta@db:5432/paleta`
- `UPLOAD_FOLDER = static/uploads`
- `MAX_CONTENT_LENGTH = 16 MB`
- Разрешенные расширения изображений: `png`, `jpg`, `jpeg`, `webp`
- Границы количества цветов: `MIN_COLOR_COUNT = 3`, `MAX_COLOR_COUNT = 15`

Если хотите использовать другую СУБД, передайте нужный URL через `DATABASE_URL`.

<a id="usage-ru"></a>

## Как пользоваться

### Режим гостя (без регистрации)

Доступно:

- извлечение палитры из изображения,
- генерация случайных палитр,
- редактирование и копирование HEX-кодов,
- экспорт палитр.

### Режим авторизованного пользователя

Дополнительно доступно:

- сохранение палитр в аккаунт,
- переименование и удаление палитр,
- поиск, фильтрация и сортировка в разделе "Мои палитры",
- повторное использование недавних загрузок,
- восстановление пароля через email (если контакт привязан к аккаунту).

### Базовый сценарий

1. Откройте главную страницу (`/`).
2. Загрузите изображение (или перейдите на `/generatePalet` для случайной генерации).
3. Выберите количество цветов и запустите генерацию/пересчет.
4. При необходимости отредактируйте цвета.
5. Экспортируйте или сохраните палитру.
6. Управляйте сохраненными палитрами на странице `/myPalet`.

### Требования к паролю при регистрации

- длина от 10 до 16 символов;
- минимум одна заглавная буква;
- минимум одна строчная буква;
- минимум одна цифра;
- минимум один спецсимвол;
- без пробелов;
- при регистрации нужно указать email для восстановления.

<a id="api-ru"></a>

## API-эндпоинты

| Метод    | Эндпоинт                            | Описание                                             |
| -------- | ----------------------------------- | ---------------------------------------------------- |
| `POST`   | `/api/upload`                       | Загрузка изображения и извлечение палитры            |
| `POST`   | `/api/palettes/save`                | Сохранение палитры (нужен вход)                      |
| `POST`   | `/api/palettes/rename/<palette_id>` | Переименование палитры (нужен вход)                  |
| `DELETE` | `/api/palettes/delete/<palette_id>` | Удаление палитры (нужен вход)                        |
| `POST`   | `/api/export?format=<type>`         | Экспорт палитры (`json`, `gpl`, `ase`, `csv`, `png`, `aco`) |
| `GET`    | `/static/uploads/<filename>`        | Выдача загруженного изображения                      |

<a id="structure-ru"></a>

## Структура проекта

```text
Paleta/
├─ app.py
├─ config.py
├─ extensions.py
├─ models/
├─ routes/
├─ utils/
├─ templates/
├─ static/
├─ LICENCE
├─ requirements.txt
├─ README.md
└─ README.ru.md
```

<a id="tests-ru"></a>

## Тестирование

Автотесты сейчас не закоммичены в этот репозиторий.

Чеклист ручной smoke-проверки:

1. Зарегистрироваться и войти в систему.
2. Загрузить изображение и сгенерировать палитру.
3. Пересчитать палитру с другим количеством цветов.
4. Сохранить палитру и проверить ее наличие в "Моих палитрах".
5. Переименовать и удалить палитру.
6. Проверить экспорт во всех поддерживаемых форматах.

<a id="roadmap-ru"></a>

## Roadmap

- Добавить автоматические тесты (`pytest`).
- Добавить миграции БД (`Flask-Migrate` / Alembic).
- Ввести отдельные профили конфигурации для production.
- Усилить i18n QA и закрыть оставшиеся пробелы в переводах.

<a id="contrib-ru"></a>

## Как внести вклад

Контрибьюции приветствуются.

Подробные правила участия:
[`CONTRIBUTING.ru.md`](CONTRIBUTING.ru.md) (RU),
[`CONTRIBUTING.md`](CONTRIBUTING.md) (EN).

1. Сделайте fork репозитория.
2. Создайте ветку: `git checkout -b feature/your-feature-name`.
3. Зафиксируйте изменения: `git commit -m "Add: your feature"`.
4. Отправьте ветку в свой репозиторий: `git push origin feature/your-feature-name`.
5. Откройте Pull Request с понятным описанием и шагами проверки.

<a id="author-ru"></a>

## Автор

- Диана Конанерова
- Юлия Тюрина

<a id="license-ru"></a>

## Лицензия

Проект распространяется по лицензии MIT.

См. файлы:

- [`LICENCE`](LICENCE)
