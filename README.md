# Paleta

<p align="right">
  🌍  <strong>Язык:</strong>
  🇬🇧  English |
  🇷🇺  <a href="README.ru.md">Русский</a>
</p>

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-black.svg)](https://flask.palletsprojects.com/)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#)

Paleta is a web app for generating, editing, saving, and exporting color palettes.
You can build palettes from uploaded images (dominant color extraction with KMeans) or generate random palettes, then manage them in your personal account.

The project is aimed at designers, frontend developers, and anyone who works with color systems and needs a fast workflow from image to ready-to-use color codes.

Production deployment guide (PostgreSQL + Docker + Nginx + HTTPS): `DEPLOYMENT.ru.md`.

## Table of Contents

1. [Why Paleta](#why-paleta)
2. [Key Features](#key-features)
3. [Tech Stack](#tech-stack)
4. [How It Works](#how-it-works)
5. [Installation and Setup](#installation-and-setup)
6. [Run the Project](#run-the-project)
7. [Configuration](#configuration)
8. [Usage Guide](#usage-guide)
9. [API Endpoints](#api-endpoints)
10. [Project Structure](#project-structure)
11. [Testing](#testing)
12. [Roadmap](#roadmap)
13. [Contributing](#contributing)
14. [Author](#author)
15. [License](#license)

## Why Paleta

### Goal

To provide a practical, browser-based tool for turning visual references into reusable color palettes.

### Problem It Solves

- Manual color picking from images is slow and inconsistent.
- Exporting palettes to design-tool formats often requires extra tools.
- Managing multiple palettes in one place is inconvenient without authentication and storage.

### What Was Learned During Development

- Building modular Flask architecture with separated routes and utilities.
- Integrating image processing and color clustering (Pillow + NumPy + scikit-learn KMeans).
- Implementing authentication and per-user data management with Flask-Login + SQLAlchemy.
- Supporting multi-format export workflows (JSON, GPL, ASE, CSV, ACO).

### What Makes It Different

- Two generation modes: from image and random.
- Inline palette editing (color picker + HEX field + copy to clipboard).
- Palette management inside account (save, rename, delete, filter, sort).
- Ready exports for both development and design tools.

## Key Features

- Image upload with drag-and-drop support.
- Dominant color extraction from image using KMeans.
- Random palette generation.
- Palette editing (HEX + picker), re-analysis with a custom number of colors.
- Export formats: `JSON`, `GPL`, `ASE`, `CSV`, `ACO`.
- User authentication (register/login/logout).
- Personal palette library with search, filters, and sorting.
- Recent image uploads (last 7 days) for signed-in users.
- Automatic cleanup of old uploads on app startup.

## Tech Stack

- `Python 3.12`
- `Flask 2.3.3`
- `Flask-SQLAlchemy`
- `Flask-Login`
- `Flask-CORS`
- `Flask-Migrate` (Alembic)
- `PyJWT`
- `Pillow`
- `NumPy`
- `scikit-learn` (KMeans)
- `SQLite` (default local DB) / `PostgreSQL` (production target)
- `Bootstrap 5` + Vanilla JavaScript

## How It Works

1. User uploads an image.
2. Backend resizes it and runs KMeans clustering.
3. Dominant RGB colors are converted to HEX.
4. User edits, copies, exports, or saves the palette.
5. Saved palettes are linked to the authenticated account and managed in "My Palettes".

## Installation and Setup

### Prerequisites

- `git`
- `Python 3.10+` (recommended `3.12`)
- `pip`

### 1) Clone repository

```bash
git clone <your-repo-url>
cd Paleta
```

### 2) Create and activate virtual environment

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

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Initialize database schema (first run)

Linux/macOS:

```bash
flask --app app db upgrade
```

Windows (PowerShell):

```bash
flask --app app db upgrade
```

## Run the Project

### Option A: direct run

Linux/macOS:

```bash
python3 app.py
```

Windows (PowerShell):

```bash
python app.py
```

### Option B: Flask CLI

```bash
flask --app app run
```

Open in browser: `http://127.0.0.1:5000`

## Configuration

Main config is in `config.py`.

### Environment variables

- `SECRET_KEY` (required in `production`, optional in local development)
- `DATABASE_URL` (optional; defaults to local SQLite in development and `/app/instance` SQLite in production)
- `AUTO_CREATE_TABLES` (dev fallback for `db.create_all`; default: `true` in development, `false` in production)
- `FLASK_ENV` (`production` for prod setup)
- `SESSION_COOKIE_SECURE` (`true` by default in production, `false` in development)
- `CORS_ENABLED` (`false` by default; enable only if API is called from another origin)
- `CORS_ORIGINS` (comma-separated list of allowed origins when `CORS_ENABLED=true`)
- `JWT_SECRET_KEY` (separate secret for JWT signing; falls back to `SECRET_KEY` if not set)
- `JWT_ACCESS_TTL_MINUTES` (default `15`)
- `JWT_REFRESH_TTL_DAYS` (default `30`)
- `JWT_ISSUER` (default `paleta`)
- `JWT_AUDIENCE` (default `paleta-mobile`)
- `MAX_IMAGE_PIXELS` (max image resolution in pixels; default `20000000`)
- `PASSWORD_RESET_CODE_TTL_MINUTES` (reset code lifetime in minutes; default `15`)
- `PASSWORD_RESET_MAX_ATTEMPTS` (max code attempts before forcing re-request; default `5`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` (email delivery for password reset)
- `SMTP_USE_TLS`, `SMTP_USE_SSL` (secure transport options for SMTP)
- `SMS_API_URL`, `SMS_API_TOKEN`, `SMS_API_TIMEOUT`, `SMS_SENDER_NAME` (optional SMS delivery provider)

Example (Linux/macOS):

```bash
export SECRET_KEY="replace-with-a-secure-random-value"
export JWT_SECRET_KEY="replace-with-another-secure-random-value"
export DATABASE_URL="postgresql+psycopg://paleta:paleta_password@localhost:5432/paleta"
export FLASK_ENV="development"
export SESSION_COOKIE_SECURE="false"
export CORS_ENABLED="false"
export AUTO_CREATE_TABLES="true"
export JWT_ACCESS_TTL_MINUTES="15"
export JWT_REFRESH_TTL_DAYS="30"
export MAX_IMAGE_PIXELS="20000000"
export PASSWORD_RESET_CODE_TTL_MINUTES="15"
export PASSWORD_RESET_MAX_ATTEMPTS="5"
```

### Default app settings

- `SQLALCHEMY_DATABASE_URI` comes from `DATABASE_URL`
- default DB URL (if not set):
  - development: `sqlite:///paleta.db`
  - production: `sqlite:////app/instance/paleta.db`
- `UPLOAD_FOLDER = static/uploads`
- `MAX_CONTENT_LENGTH = 16 MB`
- Allowed image extensions: `png`, `jpg`, `jpeg`, `webp`

If you want another DB engine, pass a different value via `DATABASE_URL`.

## Usage Guide

### Guest mode (without account)

You can:

- extract palette from image,
- generate random palettes,
- edit and copy HEX colors,
- export palettes.

### Authenticated mode

You also get:

- saving palettes to your personal library,
- rename/delete palettes,
- search/filter/sort in "My Palettes",
- quick reuse of recent uploaded images,
- password recovery via email or phone (if contact is attached to account).

### Basic flow

1. Open home page (`/`).
2. Upload image (or go to `/generatePalet` for random palette generation).
3. Select number of colors and generate/recalculate palette.
4. Edit colors if needed.
5. Export or save palette.
6. Manage saved palettes at `/myPalet`.

### Authentication rules

Registration password requirements:

- length 10 to 128 characters,
- at least one uppercase letter,
- at least one lowercase letter,
- at least one digit,
- at least one special character,
- must not contain spaces,
- registration requires at least one recovery contact (email or phone).

## API Endpoints

### Mobile API v1 (JWT)

| Method   | Endpoint                         | Description                                          |
| -------- | -------------------------------- | ---------------------------------------------------- |
| `POST`   | `/api/v1/auth/login`             | Login, return access+refresh tokens                 |
| `POST`   | `/api/v1/auth/refresh`           | Rotate refresh token and issue new token pair       |
| `POST`   | `/api/v1/auth/logout`            | Revoke refresh token                                 |
| `GET`    | `/api/v1/users/me`               | Current user profile (JWT required)                 |
| `GET`    | `/api/v1/palettes`               | Palette list with cursor pagination (JWT required)  |
| `POST`   | `/api/v1/palettes`               | Create palette (JWT required)                       |
| `PATCH`  | `/api/v1/palettes/<palette_id>`  | Update palette name/colors (JWT required)           |
| `DELETE` | `/api/v1/palettes/<palette_id>`  | Delete palette (JWT required)                       |
| `POST`   | `/api/v1/upload`                 | Upload image and extract palette                     |
| `POST`   | `/api/v1/export?format=<type>`   | Export palette (`json`, `gpl`, `ase`, `csv`, `aco`) |

Response contract:
- success: `{ "success": true, "data": ..., "meta": ... }`
- error: `{ "success": false, "error": { "code": "...", "message": "...", "details": ... } }`

### Legacy Web API (session + CSRF)

| Method   | Endpoint                            | Description                                         |
| -------- | ----------------------------------- | --------------------------------------------------- |
| `POST`   | `/api/upload`                       | Upload image and extract palette                    |
| `POST`   | `/api/palettes/save`                | Save palette (login required)                       |
| `POST`   | `/api/palettes/rename/<palette_id>` | Rename palette (login required)                     |
| `DELETE` | `/api/palettes/delete/<palette_id>` | Delete palette (login required)                     |
| `POST`   | `/api/export?format=<type>`         | Export palette (`json`, `gpl`, `ase`, `csv`, `aco`) |
| `GET`    | `/static/uploads/<filename>`        | Serve uploaded image                                |

## Project Structure

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
├─ LICENSE
├─ LICENCE
├─ requirements.txt
├─ README.md
└─ README.ru.md
```

## Testing

Automated tests are available with `pytest`.

Run:

```bash
pytest
```

Manual smoke test checklist:

1. Register and login.
2. Upload image and generate palette.
3. Recalculate palette with a different color count.
4. Save palette and verify it appears in "My Palettes".
5. Rename and delete palette.
6. Export palette in all supported formats.

## Roadmap

- Add production-ready config profiles.
- Implement PNG export.
- Add i18n (currently UI texts are mostly Russian).

## Contributing

Contributions are welcome.

Please read the full contribution guides:
[`CONTRIBUTING.md`](CONTRIBUTING.md) (EN),
[`CONTRIBUTING.ru.md`](CONTRIBUTING.ru.md) (RU).

1. Fork the repo.
2. Create a branch: `git checkout -b feature/your-feature-name`.
3. Commit changes: `git commit -m "Add: your feature"`.
4. Push branch: `git push origin feature/your-feature-name`.
5. Open a Pull Request with clear description and test steps.

## Author

- Diana Konanerova
- Yuliya Tyurina

## License

This project is licensed under the MIT License.

See:

- [`LICENCE`](LICENCE)
