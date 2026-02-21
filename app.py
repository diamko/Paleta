"""
Название: «Paleta»
Разработала: Конанерова Диана Максимовна
Группа: ТИП-62
Дата и номер версии: 2026-02-07 v1.0
Язык: Python (Flask)
Краткое описание: веб-приложение для генерации и управления цветовыми палитрами на основе изображений
"""

import hmac
import os
import secrets

from flask import (
    Flask,
    abort,
    flash,
    g,
    has_request_context,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from werkzeug.routing import BuildError

from config import Config
from extensions import babel, cors, db, login_manager, migrate
import models  # noqa: F401 - регистрирует модели для db.create_all()
from routes.pages import register_routes as register_page_routes
from routes.auth import register_routes as register_auth_routes
from routes.api import register_routes as register_api_routes
from routes.api_v1 import register_routes as register_api_v1_routes
from utils.cleanup import cleanup_old_uploads
from flask_babel import gettext as _
from utils.i18n import is_supported_language, resolve_request_language
from utils.rate_limit import InMemoryRateLimiter


def create_app(config_override: dict | None = None) -> Flask:
    """Фабрика приложения, собирающая все модули воедино."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    def select_locale() -> str:
        return getattr(g, "lang", app.config["DEFAULT_LANGUAGE"])

    babel.init_app(app, locale_selector=select_locale)

    if app.config["CORS_ENABLED"]:
        cors.init_app(
            app,
            resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        )

    login_manager.login_view = "login"
    login_manager.login_message = "Пожалуйста, войдите, чтобы получить доступ к этой странице."
    login_manager.login_message_category = "error"
    app.extensions["rate_limiter"] = InMemoryRateLimiter()

    # Гарантируем наличие служебных директорий
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Регистрация роутов по модулям
    register_page_routes(app)
    register_auth_routes(app)
    register_api_routes(app)
    register_api_v1_routes(app)

    with app.app_context():
        # Dev fallback для локального запуска без миграций.
        if app.config["AUTO_CREATE_TABLES"]:
            db.create_all()

    def _resolve_request_lang(url_lang: str | None = None) -> str:
        supported_languages: tuple[str, ...] = app.config["SUPPORTED_LANGUAGES"]
        return resolve_request_language(
            request=request,
            url_lang=url_lang,
            supported_languages=supported_languages,
            cookie_name=app.config["LANG_COOKIE_NAME"],
            default_language=app.config["DEFAULT_LANGUAGE"],
            ru_country_codes=app.config["RU_COUNTRY_CODES"],
        )

    def _ensure_csrf_token() -> str:
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    def _is_csrf_valid() -> bool:
        expected = session.get("csrf_token")
        provided = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or not provided:
            return False
        return hmac.compare_digest(expected, provided)

    def _language_for_url() -> str:
        if not has_request_context():
            return app.config["DEFAULT_LANGUAGE"]
        return getattr(g, "lang", app.config["DEFAULT_LANGUAGE"])

    def _alternate_lang_url(target_lang: str) -> str:
        supported_languages: tuple[str, ...] = app.config["SUPPORTED_LANGUAGES"]
        if not is_supported_language(target_lang, supported_languages):
            target_lang = app.config["DEFAULT_LANGUAGE"]

        endpoint = request.endpoint
        if not endpoint:
            return url_for("index", lang=target_lang)

        if endpoint in {
            "static",
            "healthz",
            "robots_txt",
            "sitemap_xml",
            "favicon",
            "yandex_verification",
            "language_root",
        }:
            return url_for("index", lang=target_lang)

        values = dict(request.view_args or {})
        values["lang"] = target_lang

        for key, value in request.args.items():
            values.setdefault(key, value)

        try:
            return url_for(endpoint, **values)
        except BuildError:
            return url_for("index", lang=target_lang)

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        flash(_(login_manager.login_message), login_manager.login_message_category)
        next_url = request.full_path if request.query_string else request.path
        if next_url.endswith("?"):
            next_url = next_url[:-1]
        return redirect(url_for("login", lang=_language_for_url(), next=next_url))

    @app.url_defaults
    def add_language_code(endpoint, values):
        if "lang" in values:
            return

        if endpoint in {
            "static",
            "robots_txt",
            "sitemap_xml",
            "healthz",
            "favicon",
            "yandex_verification",
            "language_root",
            "uploaded_file",
        }:
            return

        if not has_request_context():
            return

        for rule in app.url_map.iter_rules(endpoint):
            if "lang" in rule.arguments:
                values["lang"] = _language_for_url()
                return

    @app.before_request
    def resolve_request_language_middleware():
        supported_languages: tuple[str, ...] = app.config["SUPPORTED_LANGUAGES"]
        url_lang = (request.view_args or {}).get("lang") if request.view_args else None

        if url_lang is not None and not is_supported_language(url_lang, supported_languages):
            abort(404)

        g.lang = _resolve_request_lang(url_lang)

    @app.context_processor
    def inject_template_globals():
        return {
            "csrf_token": _ensure_csrf_token(),
            "current_lang": _language_for_url(),
            "supported_langs": app.config["SUPPORTED_LANGUAGES"],
            "alternate_lang_url": _alternate_lang_url,
            "js_i18n": {
                "hex_copied": _("HEX код скопирован!"),
                "copy_error": _("Ошибка копирования:"),
                "bootstrap_missing": _("Bootstrap не загружен!"),
                "bootstrap_loaded": _("Bootstrap загружен успешно"),
                "upload_image_first": _("Сначала загрузите изображение!"),
                "palette_recalculated": _("Палитра пересчитана!"),
                "palette_recalculate_error": _("Ошибка при пересчете палитры"),
                "palette_recalculate_fail": _("Произошла ошибка при пересчете"),
                "create_palette_first": _("Сначала создайте палитру!"),
                "palette_name_spaces": _("Название палитры не может состоять только из пробелов"),
                "session_expired_login": _("Сессия истекла. Пожалуйста, войдите снова."),
                "save_error": _("Ошибка при сохранении"),
                "palette_saved": _("Палитра сохранена!"),
                "save_palette_error": _("Ошибка при сохранении палитры"),
                "export_error": _("Ошибка при экспорте"),
                "hex_validation_error": _("Введите корректный HEX-код, например #A1B2C3"),
                "ready_for_new_upload": _("Готово для новой загрузки!"),
                "select_image": _("Пожалуйста, выберите изображение"),
                "file_too_large": _("Файл слишком большой. Максимальный размер: 16 МБ"),
                "upload_error": _("Ошибка загрузки изображения"),
                "analyze_error": _("Ошибка при анализе изображения"),
                "upload_file_error": _("Произошла ошибка при загрузке файла"),
                "saved_image_load_error": _("Не удалось загрузить сохранённое изображение"),
                "saved_image_use_error": _("Произошла ошибка при использовании сохранённого изображения"),
                "use_upload": _("Использовать"),
                "recent_image_alt": _("Недавнее изображение"),
                "palette_deleted": _("Палитра удалена!"),
                "delete_error_prefix": _("Ошибка при удалении:"),
                "delete_error": _("Произошла ошибка при удалении"),
                "delete_modal_prompt": _("Вы уверены, что хотите удалить палитру"),
                "rename_empty": _("Название палитры не может быть пустым."),
                "rename_success": _("Название палитры обновлено!"),
                "rename_error": _("Ошибка при переименовании палитры"),
                "rename_unknown_error": _("Произошла ошибка при переименовании палитры"),
                "colors_copied": _("Цвета скопированы в буфер обмена!"),
                "generate_palette_first": _("Сначала сгенерируйте палитру!"),
                "default_palette_name": _("Моя палитра"),
                "copy_hex_title": _("Скопировать HEX"),
                "color_picker_label": _("Выбор цвета %(index)s", index="{index}"),
                "color_hex_label": _("HEX цвета %(index)s", index="{index}"),
                "color_marker_label": _("Маркер цвета %(index)s", index="{index}"),
                "lang": _language_for_url(),
            },
        }

    @app.before_request
    def enforce_csrf():
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return None

        if request.endpoint in {"healthz"}:
            return None

        if request.path.startswith("/api/v1/"):
            return None

        if _is_csrf_valid():
            return None

        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": _("Недействительный CSRF-токен. Обновите страницу и повторите попытку."),
                    }
                ),
                400,
            )

        flash(_("Сессия формы истекла. Обновите страницу и попробуйте снова."), "error")
        return redirect(request.referrer or url_for("index", lang=_language_for_url()))

    @app.after_request
    def persist_lang_cookie(response):
        supported_languages: tuple[str, ...] = app.config["SUPPORTED_LANGUAGES"]
        request_lang = (request.view_args or {}).get("lang") if request.view_args else None

        if request_lang and is_supported_language(request_lang, supported_languages):
            cookie_name = app.config["LANG_COOKIE_NAME"]
            if request.cookies.get(cookie_name) != request_lang:
                response.set_cookie(
                    cookie_name,
                    request_lang,
                    max_age=app.config["LANG_COOKIE_MAX_AGE"],
                    secure=app.config["SESSION_COOKIE_SECURE"],
                    httponly=False,
                    samesite="Lax",
                    path="/",
                )

        return response

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        # Очистка старых загрузок при запуске приложения
        cleanup_old_uploads()
    is_production = os.environ.get("FLASK_ENV", "").lower() == "production"
    app.run(debug=not is_production)
