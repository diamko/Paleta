"""
Программа: «Paleta» – веб-приложение для работы с цветовыми палитрами.
Модуль: config.py – конфигурация приложения.

Назначение модуля:
- Определение базовых параметров приложения Flask (секретный ключ, строка подключения к БД).
- Настройка параметров загрузки файлов (папка, максимальный размер, допустимые расширения).
- Предоставление вспомогательной функции allowed_file() для проверки расширения файлов.
"""

import os
import warnings


def _get_env_bool(name: str, default: bool = False) -> bool:
    """Преобразует переменную окружения в bool."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_int(name: str, default: int) -> int:
    """Преобразует переменную окружения в int."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def _get_env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Преобразует переменную окружения вида 'a,b,c' в список."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_production() -> bool:
    """Определяет production-режим по FLASK_ENV."""
    return os.environ.get("FLASK_ENV", "").strip().lower() == "production"


class Config:
    """Базовая конфигурация приложения."""

    _PRODUCTION = _is_production()

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if _PRODUCTION:
            raise RuntimeError(
                "SECRET_KEY environment variable is required in production. "
                "Set a strong random value before starting the app."
            )
        SECRET_KEY = "dev-insecure-secret-key"
        warnings.warn(
            "SECRET_KEY is not set. Using insecure development fallback key.",
            RuntimeWarning,
            stacklevel=1,
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:////app/instance/paleta.db" if _PRODUCTION else "sqlite:///paleta.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_TABLES = _get_env_bool("AUTO_CREATE_TABLES", default=not _PRODUCTION)
    SESSION_COOKIE_SECURE = _get_env_bool("SESSION_COOKIE_SECURE", default=_PRODUCTION)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE

    CORS_ENABLED = _get_env_bool("CORS_ENABLED", default=False)
    CORS_ORIGINS = _get_env_list(
        "CORS_ORIGINS",
        default=[
            "http://127.0.0.1:5000",
            "http://localhost:5000",
            "https://diamko.ru",
            "https://www.diamko.ru",
        ],
    )

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_IMAGE_FORMATS = {"png", "jpeg", "webp"}
    MAX_IMAGE_PIXELS = _get_env_int("MAX_IMAGE_PIXELS", 20_000_000)
    MIN_COLOR_COUNT = _get_env_int("MIN_COLOR_COUNT", 3)
    MAX_COLOR_COUNT = _get_env_int("MAX_COLOR_COUNT", 15)

    PASSWORD_RESET_CODE_TTL_MINUTES = _get_env_int("PASSWORD_RESET_CODE_TTL_MINUTES", 15)
    PASSWORD_RESET_MAX_ATTEMPTS = _get_env_int("PASSWORD_RESET_MAX_ATTEMPTS", 5)

    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
    SMTP_PORT = _get_env_int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "").strip()
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "").strip()
    SMTP_USE_TLS = _get_env_bool("SMTP_USE_TLS", default=True)
    SMTP_USE_SSL = _get_env_bool("SMTP_USE_SSL", default=False)

    SMS_API_URL = os.environ.get("SMS_API_URL", "").strip()
    SMS_API_TOKEN = os.environ.get("SMS_API_TOKEN", "").strip()
    SMS_API_TIMEOUT = _get_env_int("SMS_API_TIMEOUT", 8)
    SMS_SENDER_NAME = os.environ.get("SMS_SENDER_NAME", "Paleta").strip()

    SUPPORTED_LANGUAGES = ("ru", "en")
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en").strip().lower() or "en"
    LANG_COOKIE_NAME = os.environ.get("LANG_COOKIE_NAME", "site_lang").strip() or "site_lang"
    LANG_COOKIE_MAX_AGE = _get_env_int("LANG_COOKIE_MAX_AGE", 31536000)
    RU_COUNTRY_CODES = {
        code.strip().upper()
        for code in _get_env_list("RU_COUNTRY_CODES", default=["RU"])
        if code.strip()
    } or {"RU"}

    JWT_ACCESS_TTL_MINUTES = _get_env_int("JWT_ACCESS_TTL_MINUTES", 15)
    JWT_REFRESH_TTL_DAYS = _get_env_int("JWT_REFRESH_TTL_DAYS", 30)
    JWT_ISSUER = os.environ.get("JWT_ISSUER", "paleta").strip() or "paleta"
    JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "paleta-mobile").strip() or "paleta-mobile"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
        )
