"""
Versioned API v1 for mobile clients.
"""

import os
import tempfile
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, g, request, send_file
from flask_babel import gettext as _
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from config import Config
from extensions import db
from models.palette import Palette
from models.upload import Upload
from models.user import User
from utils.api_response import api_error, api_success
from utils.export_handler import export_palette_data
from utils.image_processor import extract_colors_from_image
from utils.jwt_service import (
    AuthError,
    get_user_from_access_token,
    issue_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)
from utils.pagination import decode_cursor, encode_cursor
from utils.palette_service import (
    PaletteValidationError,
    clamp_color_count,
    normalize_palette_colors,
    resolve_palette_name,
    serialize_palette,
    validate_uploaded_image,
)
from utils.rate_limit import get_client_identifier


def _rate_limited(bucket: str, limit: int, window_seconds: int, identity: str | None = None) -> bool:
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        return False

    rate_identity = identity or get_client_identifier()
    return not limiter.is_allowed(f"{bucket}:{rate_identity}", limit, window_seconds)


def _bearer_token(required: bool = True) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        if required:
            raise AuthError("AUTH_REQUIRED", "Требуется токен авторизации", 401)
        return None

    if not auth_header.startswith("Bearer "):
        raise AuthError("AUTH_INVALID_TOKEN", "Некорректный заголовок авторизации", 401)

    token = auth_header[len("Bearer ") :].strip()
    if not token:
        raise AuthError("AUTH_INVALID_TOKEN", "Пустой токен авторизации", 401)
    return token


def _auth_error_response(exc: AuthError):
    return api_error(exc.code, _(exc.message), status=exc.status)


def require_api_user(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            token = _bearer_token(required=True)
            g.api_user = get_user_from_access_token(token)
        except AuthError as exc:
            return _auth_error_response(exc)
        return view_func(*args, **kwargs)

    return wrapper


def _optional_api_user() -> tuple[User | None, tuple | None]:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, None

    try:
        token = _bearer_token(required=False)
        if not token:
            return None, None
        return get_user_from_access_token(token), None
    except AuthError as exc:
        return None, _auth_error_response(exc)


def _palette_defaults() -> tuple[str, set[str]]:
    default_base_name = _("Моя палитра")
    default_names = {
        default_base_name,
        _("Без названия"),
        "Untitled Palette",
        "Random Palette",
        "",
    }
    return default_base_name, default_names


def _palette_not_found() -> tuple:
    return api_error("NOT_FOUND", _("Палитра не найдена"), status=404)


def register_routes(app):
    bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

    @bp.post("/auth/login")
    def login():
        if _rate_limited("api_v1_login_ip", limit=30, window_seconds=10 * 60):
            return api_error("RATE_LIMITED", _("Слишком много попыток входа. Попробуйте позже."), status=429)

        payload = request.get_json(silent=True) or {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        device_id = (payload.get("device_id") or "android").strip() or "android"
        device_name = (payload.get("device_name") or "Android Device").strip() or "Android Device"

        username_key = username.lower() or "anonymous"
        if _rate_limited("api_v1_login_user", limit=12, window_seconds=10 * 60, identity=username_key):
            return api_error("RATE_LIMITED", _("Слишком много попыток входа для этого пользователя."), status=429)

        if not username or not password:
            return api_error("VALIDATION_ERROR", _("Требуются username и password"), status=400)

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            return api_error("AUTH_INVALID_CREDENTIALS", _("Неверное имя пользователя или пароль"), status=401)

        tokens = issue_token_pair(user.id, device_id=device_id, device_name=device_name)
        db.session.commit()

        return api_success(
            {
                **tokens,
                "user": {
                    "id": user.id,
                    "username": user.username,
                },
            }
        )

    @bp.post("/auth/refresh")
    def refresh():
        if _rate_limited("api_v1_refresh", limit=60, window_seconds=10 * 60):
            return api_error("RATE_LIMITED", _("Слишком много запросов обновления токена."), status=429)

        payload = request.get_json(silent=True) or {}
        refresh_token = (payload.get("refresh_token") or "").strip()
        device_id = (payload.get("device_id") or "android").strip() or "android"
        device_name = (payload.get("device_name") or "Android Device").strip() or "Android Device"

        if not refresh_token:
            return api_error("VALIDATION_ERROR", _("Не передан refresh token"), status=400)

        try:
            _, tokens = rotate_refresh_token(
                refresh_token,
                device_id=device_id,
                device_name=device_name,
            )
            db.session.commit()
        except AuthError as exc:
            db.session.rollback()
            return _auth_error_response(exc)

        return api_success(tokens)

    @bp.post("/auth/logout")
    def logout():
        payload = request.get_json(silent=True) or {}
        refresh_token = (payload.get("refresh_token") or "").strip()
        if not refresh_token:
            return api_error("VALIDATION_ERROR", _("Не передан refresh token"), status=400)

        revoked = revoke_refresh_token(refresh_token)
        db.session.commit()

        return api_success({"revoked": revoked})

    @bp.get("/users/me")
    @require_api_user
    def me():
        user = g.api_user
        contact = user.contact
        return api_success(
            {
                "id": user.id,
                "username": user.username,
                "contact": {
                    "email": contact.email if contact else None,
                    "phone": contact.phone if contact else None,
                },
            }
        )

    @bp.get("/palettes")
    @require_api_user
    def list_palettes():
        limit = request.args.get("limit", default=20, type=int)
        limit = max(1, min(limit, 50))

        raw_cursor = request.args.get("cursor")
        cursor = decode_cursor(raw_cursor)
        if raw_cursor and cursor is None:
            return api_error("VALIDATION_ERROR", _("Некорректный cursor"), status=400)

        query = Palette.query.filter_by(user_id=g.api_user.id)
        if cursor is not None:
            cursor_created_at, cursor_id = cursor
            query = query.filter(
                or_(
                    Palette.created_at < cursor_created_at,
                    and_(Palette.created_at == cursor_created_at, Palette.id < cursor_id),
                )
            )

        items = query.order_by(Palette.created_at.desc(), Palette.id.desc()).limit(limit + 1).all()
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]

        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.id)

        meta = {
            "limit": limit,
            "next_cursor": next_cursor,
        }
        return api_success([serialize_palette(item) for item in items], meta=meta)

    @bp.post("/palettes")
    @require_api_user
    def create_palette():
        payload = request.get_json(silent=True) or {}
        colors = normalize_palette_colors(payload.get("colors", []), Config.MIN_COLOR_COUNT, Config.MAX_COLOR_COUNT)
        if not colors:
            return api_error("VALIDATION_ERROR", _("Палитра должна содержать корректные HEX-цвета"), status=400)

        default_base_name, default_names = _palette_defaults()
        try:
            palette_name = resolve_palette_name(
                user_id=g.api_user.id,
                requested_name=payload.get("name"),
                default_base_name=default_base_name,
                default_names=default_names,
            )
        except PaletteValidationError as exc:
            return api_error(exc.code, _(exc.message), status=exc.status)

        palette = Palette(name=palette_name, colors=colors, user_id=g.api_user.id)
        db.session.add(palette)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return api_error("PALETTE_NAME_CONFLICT", _("У вас уже есть палитра с таким названием"), status=409)

        return api_success(serialize_palette(palette), status=201)

    @bp.patch("/palettes/<int:palette_id>")
    @require_api_user
    def update_palette(palette_id: int):
        payload = request.get_json(silent=True) or {}
        palette = db.session.get(Palette, palette_id)
        if not palette:
            return _palette_not_found()

        if palette.user_id != g.api_user.id:
            return api_error("FORBIDDEN", _("У вас нет прав на изменение этой палитры"), status=403)

        has_changes = False

        if "name" in payload:
            new_name = (payload.get("name") or "").strip()
            if not new_name:
                return api_error("VALIDATION_ERROR", _("Название палитры не может быть пустым"), status=400)
            palette.name = new_name
            has_changes = True

        if "colors" in payload:
            colors = normalize_palette_colors(payload.get("colors", []), Config.MIN_COLOR_COUNT, Config.MAX_COLOR_COUNT)
            if not colors:
                return api_error("VALIDATION_ERROR", _("Палитра должна содержать корректные HEX-цвета"), status=400)
            palette.colors = colors
            has_changes = True

        if not has_changes:
            return api_error("VALIDATION_ERROR", _("Нет данных для обновления"), status=400)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return api_error("PALETTE_NAME_CONFLICT", _("У вас уже есть палитра с таким названием"), status=409)

        return api_success(serialize_palette(palette))

    @bp.delete("/palettes/<int:palette_id>")
    @require_api_user
    def delete_palette(palette_id: int):
        palette = db.session.get(Palette, palette_id)
        if not palette:
            return _palette_not_found()

        if palette.user_id != g.api_user.id:
            return api_error("FORBIDDEN", _("У вас нет прав на удаление этой палитры"), status=403)

        db.session.delete(palette)
        db.session.commit()
        return api_success({"deleted": True})

    @bp.post("/upload")
    def upload_image():
        if _rate_limited("api_v1_upload", limit=40, window_seconds=10 * 60):
            return api_error("RATE_LIMITED", _("Слишком много загрузок. Попробуйте позже."), status=429)

        if "image" not in request.files:
            return api_error("VALIDATION_ERROR", _("Файл не был загружен"), status=400)

        file = request.files["image"]
        if file.filename == "":
            return api_error("VALIDATION_ERROR", _("Файл не выбран"), status=400)

        if not Config.allowed_file(file.filename):
            return api_error("VALIDATION_ERROR", _("Недопустимый тип файла"), status=400)

        try:
            extension = validate_uploaded_image(
                file,
                allowed_formats=Config.ALLOWED_IMAGE_FORMATS,
                max_pixels=Config.MAX_IMAGE_PIXELS,
            )
        except PaletteValidationError as exc:
            return api_error(exc.code, _(exc.message), status=exc.status)

        optional_user, auth_error = _optional_api_user()
        if auth_error:
            return auth_error

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:12]}.{extension}"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)

        file.save(filepath)
        color_count = clamp_color_count(
            request.form.get("color_count", 5, type=int),
            Config.MIN_COLOR_COUNT,
            Config.MAX_COLOR_COUNT,
        )

        try:
            palette = extract_colors_from_image(filepath, color_count)
        except Exception:
            current_app.logger.exception("Ошибка извлечения цветов из изображения")
            return api_error("INTERNAL_ERROR", _("Не удалось извлечь цвета из изображения"), status=500)

        upload_record = Upload(
            filename=unique_filename,
            user_id=optional_user.id if optional_user else None,
        )
        db.session.add(upload_record)
        db.session.commit()

        return api_success({"filename": unique_filename, "palette": palette})

    @bp.post("/export")
    def export_palette():
        if _rate_limited("api_v1_export", limit=120, window_seconds=10 * 60):
            return api_error("RATE_LIMITED", _("Слишком много экспортов. Попробуйте позже."), status=429)

        payload = request.get_json(silent=True) or {}
        colors = normalize_palette_colors(payload.get("colors", []), Config.MIN_COLOR_COUNT, Config.MAX_COLOR_COUNT)
        if not colors:
            return api_error("VALIDATION_ERROR", _("Не переданы корректные цвета палитры"), status=400)

        format_type = request.args.get("format", "json").lower()
        content, filename, mode = export_palette_data(colors, format_type)
        if content is None or filename is None:
            if format_type == "png":
                return api_success({"message": _("Экспорт PNG пока не реализован")})
            return api_error("VALIDATION_ERROR", _("Неподдерживаемый формат экспорта"), status=400)

        with tempfile.NamedTemporaryFile(delete=False, mode=mode, suffix=f".{format_type}") as handle:
            handle.write(content)
            temp_path = handle.name

        response = send_file(temp_path, as_attachment=True, download_name=filename)

        @response.call_on_close
        def cleanup():
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        return response

    app.register_blueprint(bp)
