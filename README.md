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
- `Pillow`
- `NumPy`
- `scikit-learn` (KMeans)
- `SQLite` (default database)
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
.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Initialize database (first run)

```bash
python3 -c "from app import app; from extensions import db; import models; app.app_context().push(); db.create_all()"
```

By default, SQLite DB is created at `instance/paleta.db`.

## Run the Project

### Option A: direct run

```bash
python3 app.py
```

### Option B: Flask CLI

```bash
flask --app app run
```

Open in browser: `http://127.0.0.1:5000`

## Configuration

Main config is in `config.py`.

### Environment variables

- `SECRET_KEY` (recommended in production)

Example (Linux/macOS):

```bash
export SECRET_KEY="replace-with-a-secure-random-value"
```

### Default app settings

- `SQLALCHEMY_DATABASE_URI = sqlite:///paleta.db`
- `UPLOAD_FOLDER = static/uploads`
- `MAX_CONTENT_LENGTH = 16 MB`
- Allowed image extensions: `png`, `jpg`, `jpeg`, `webp`

If you want another DB engine, update `SQLALCHEMY_DATABASE_URI` in `config.py`.

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
- quick reuse of recent uploaded images.

### Basic flow

1. Open home page (`/`).
2. Upload image (or go to `/generatePalet` for random palette generation).
3. Select number of colors and generate/recalculate palette.
4. Edit colors if needed.
5. Export or save palette.
6. Manage saved palettes at `/myPalet`.

### Authentication rules

Registration password requirements:
- length 4 to 16 characters,
- at least one uppercase letter,
- at least one digit,
- forbidden chars: `* & { } | +`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload image and extract palette |
| `POST` | `/api/palettes/save` | Save palette (login required) |
| `POST` | `/api/palettes/rename/<palette_id>` | Rename palette (login required) |
| `DELETE` | `/api/palettes/delete/<palette_id>` | Delete palette (login required) |
| `POST` | `/api/export?format=<type>` | Export palette (`json`, `gpl`, `ase`, `csv`, `aco`) |
| `GET` | `/static/uploads/<filename>` | Serve uploaded image |

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
├─ requirements.txt
└─ README.md
```

## Testing

Automated tests are not added yet.

Manual smoke test checklist:
1. Register and login.
2. Upload image and generate palette.
3. Recalculate palette with a different color count.
4. Save palette and verify it appears in "My Palettes".
5. Rename and delete palette.
6. Export palette in all supported formats.

## Roadmap

- Add automated test suite (`pytest`).
- Add migration support (`Flask-Migrate` / Alembic).
- Add production-ready config profiles.
- Implement PNG export.
- Add i18n (currently UI texts are mostly Russian).

## Contributing

Contributions are welcome.

1. Fork the repo.
2. Create a branch: `git checkout -b feature/your-feature-name`.
3. Commit changes: `git commit -m "Add: your feature"`.
4. Push branch: `git push origin feature/your-feature-name`.
5. Open a Pull Request with clear description and test steps.

## Author

- Diana Konanerova
- Yuliya Tyurina

## License

This repository currently does not include a `LICENSE` file.

Until a license is added, default copyright rules apply.
If you plan to open-source collaboration, add a license first (for example MIT or GPL).
