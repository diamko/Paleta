"""
Программа: «Paleta» – mobile API для Android-клиента.
Модуль: routes/mobile_api.py.
"""

from __future__ import annotations

import os
import re
import secrets
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from functools import wraps

from PIL import Image, UnidentifiedImageError
from flask import current_app, jsonify, request, send_file
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from extensions import db
from models.palette import Palette
from models.password_reset_token import PasswordResetToken
from models.upload import Upload
from models.user import User
from models.user_contact import UserContact
from utils.contact_normalizer import normalize_email
from utils.export_handler import export_palette_data
from utils.image_processor import extract_colors_from_image
from utils.rate_limit import get_client_identifier
from utils.reset_delivery import send_password_reset_code


Image.MAX_IMAGE_PIXELS = Config.MAX_IMAGE_PIXELS

_access_tokens: dict[str, int] = {}
_refresh_tokens: dict[str, int] = {}


def _envelope_ok(data=None, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def _envelope_error(message: str, code: str | None = None, status: int = 400):
    return jsonify(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
    ), status


def _rate_limited(bucket: str, limit: int, window_seconds: int, identity: str | None = None) -> bool:
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        return False

    rate_identity = identity or get_client_identifier()
    rate_key = f"{bucket}:{rate_identity}"
    return not limiter.is_allowed(rate_key, limit, window_seconds)


def _validate_username(username: str) -> str | None:
    if not username:
        return "Имя пользователя обязательно."
    if len(username) < 3:
        return "Имя пользователя должно содержать минимум 3 символа."
    if len(username) > 80:
        return "Имя пользователя не должно превышать 80 символов."
    if any(ch.isspace() for ch in username):
        return "Имя пользователя не должно содержать пробелы."
    return None


def _validate_password_strength(password: str, username: str | None = None) -> str | None:
    if not (10 <= len(password) <= 16):
        return "Пароль должен содержать от 10 до 16 символов."
    if any(ch.isspace() for ch in password):
        return "Пароль не должен содержать пробелы."
    if not any(ch.isupper() for ch in password):
        return "Пароль должен содержать хотя бы одну заглавную букву."
    if not any(ch.islower() for ch in password):
        return "Пароль должен содержать хотя бы одну строчную букву."
    if not any(ch.isdigit() for ch in password):
        return "Пароль должен содержать хотя бы одну цифру."
    if not any(not ch.isalnum() for ch in password):
        return "Пароль должен содержать хотя бы один спецсимвол."
    if username and username.lower() in password.lower():
        return "Пароль не должен содержать имя пользователя."
    return None


def _find_user_by_login(login_value: str) -> User | None:
    raw = (login_value or "").strip()
    if not raw:
        return None

    user = User.query.filter_by(username=raw).first()
    if user:
        return user

    email = normalize_email(raw)
    if email:
        user_contact = UserContact.query.filter_by(email=email).first()
        if user_contact and user_contact.user:
            return user_contact.user

    return None


def _normalize_palette_colors(colors):
    if not isinstance(colors, list):
        return None

    if not (Config.MIN_COLOR_COUNT <= len(colors) <= Config.MAX_COLOR_COUNT):
        return None

    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    normalized: list[str] = []
    for raw_color in colors:
        if not isinstance(raw_color, str):
            return None
        color = raw_color.strip()
        if not hex_pattern.match(color):
            return None
        normalized.append(color.upper())

    return normalized


def _issue_tokens(user_id: int) -> dict[str, str]:
    access = f"m_access_{secrets.token_urlsafe(24)}"
    refresh = f"m_refresh_{secrets.token_urlsafe(24)}"
    _access_tokens[access] = user_id
    _refresh_tokens[refresh] = user_id
    return {
        "access_token": access,
        "refresh_token": refresh,
    }


def _revoke_tokens(access_token: str | None = None, refresh_token: str | None = None):
    if access_token:
        _access_tokens.pop(access_token, None)
    if refresh_token:
        _refresh_tokens.pop(refresh_token, None)


def _bearer_token() -> str | None:
    raw = request.headers.get("Authorization", "")
    if not raw.startswith("Bearer "):
        return None
    token = raw[7:].strip()
    return token or None


def _mobile_user_from_access_token(access_token: str | None) -> User | None:
    if not access_token:
        return None

    user_id = _access_tokens.get(access_token)
    if not user_id:
        return None

    return db.session.get(User, int(user_id))


def _current_mobile_user_optional() -> User | None:
    return _mobile_user_from_access_token(_bearer_token())


def _serialize_user(user: User) -> dict:
    return {
        "id": int(user.id),
        "username": user.username,
        "email": (user.contact.email if user.contact and user.contact.email else ""),
    }


def _serialize_palette(palette: Palette) -> dict:
    created_at = palette.created_at
    if created_at is None:
        created_at_iso = datetime.now(UTC).isoformat()
    else:
        created_at_iso = created_at.replace(tzinfo=UTC).isoformat()

    return {
        "id": int(palette.id),
        "name": palette.name,
        "colors": list(palette.colors or []),
        "created_at": created_at_iso,
    }


def _allowed_file(filename: str) -> bool:
    return Config.allowed_file(filename)


def _validate_uploaded_image(file_storage):
    file_storage.stream.seek(0)
    try:
        with Image.open(file_storage.stream) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        return None, "Файл не является корректным изображением"
    finally:
        file_storage.stream.seek(0)

    try:
        with Image.open(file_storage.stream) as image:
            image_format = (image.format or "").lower()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None, "Файл не является корректным изображением"
    finally:
        file_storage.stream.seek(0)

    if image_format not in Config.ALLOWED_IMAGE_FORMATS:
        return None, "Недопустимый формат изображения"

    if width * height > Config.MAX_IMAGE_PIXELS:
        return None, "Изображение слишком большое по разрешению"

    format_to_extension = {"jpeg": "jpg", "png": "png", "webp": "webp"}
    return format_to_extension[image_format], None


def _clamp_color_count(raw_value: int | None) -> int:
    if raw_value is None:
        return 5
    return max(Config.MIN_COLOR_COUNT, min(Config.MAX_COLOR_COUNT, raw_value))


def _issue_reset_code(user_id: int, destination: str) -> tuple[bool, str]:
    now = datetime.utcnow()
    expires_at = now + timedelta(
        minutes=max(5, int(current_app.config.get("PASSWORD_RESET_CODE_TTL_MINUTES", 15)))
    )
    code = f"{secrets.randbelow(1_000_000):06d}"

    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).update({PasswordResetToken.used_at: now}, synchronize_session=False)

    token = PasswordResetToken(
        user_id=user_id,
        channel="email",
        destination=destination,
        code_hash=generate_password_hash(code, method="scrypt"),
        expires_at=expires_at,
    )
    db.session.add(token)
    db.session.commit()

    sent = send_password_reset_code(destination, code)
    if not sent:
        current_app.logger.warning("Не удалось отправить reset code для mobile пользователя %s", user_id)
        token.used_at = now
        db.session.commit()

    return sent, code


def _get_active_reset_token(user_id: int, destination: str) -> PasswordResetToken | None:
    now = datetime.utcnow()
    return (
        PasswordResetToken.query.filter_by(
            user_id=user_id,
            channel="email",
            destination=destination,
            used_at=None,
        )
        .filter(PasswordResetToken.expires_at > now)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )


def _with_mobile_user(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        access = _bearer_token()
        if not access:
            return _envelope_error("Требуется авторизация", code="unauthorized", status=401)

        user = _mobile_user_from_access_token(access)
        if not user:
            return _envelope_error("Сессия истекла. Выполните вход снова.", code="session_expired", status=401)

        return handler(user, access, *args, **kwargs)

    return wrapped


def register_routes(app):
    @app.post("/api/mobile/v1/auth/login")
    def mobile_login():
        try:
            if _rate_limited("mobile_login", limit=20, window_seconds=10 * 60):
                return _envelope_error("Слишком много попыток входа. Попробуйте позже.", code="rate_limited", status=429)

            payload = request.get_json(silent=True) or {}
            login = (payload.get("login") or "").strip()
            password = payload.get("password") or ""

            if not login or not password:
                return _envelope_error("Заполните логин и пароль", code="validation_error", status=400)

            user = _find_user_by_login(login)
            if not user or not check_password_hash(user.password_hash, password):
                return _envelope_error("Неверный логин или пароль", code="invalid_credentials", status=401)

            tokens = _issue_tokens(int(user.id))
            return _envelope_ok({"user": _serialize_user(user), "tokens": tokens})
        except Exception:
            current_app.logger.exception("mobile_login failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/auth/register")
    def mobile_register():
        try:
            if _rate_limited("mobile_register", limit=10, window_seconds=15 * 60):
                return _envelope_error("Слишком много попыток регистрации. Попробуйте позже.", code="rate_limited", status=429)

            payload = request.get_json(silent=True) or {}
            username = (payload.get("username") or "").strip()
            raw_email = payload.get("email") or ""
            email = normalize_email(raw_email)
            password = payload.get("password") or ""

            username_error = _validate_username(username)
            if username_error:
                return _envelope_error(username_error, code="validation_error", status=400)

            if not raw_email.strip() or not email:
                return _envelope_error("Введите корректный email.", code="validation_error", status=400)

            password_error = _validate_password_strength(password, username=username)
            if password_error:
                return _envelope_error(password_error, code="validation_error", status=400)

            if User.query.filter_by(username=username).first():
                return _envelope_error("Пользователь с таким именем уже существует", code="user_exists", status=400)

            if UserContact.query.filter_by(email=email).first():
                return _envelope_error("Этот email уже используется другим аккаунтом.", code="email_exists", status=400)

            new_user = User(username=username, password_hash=generate_password_hash(password, method="scrypt"))
            new_user.contact = UserContact(email=email)
            db.session.add(new_user)
            db.session.commit()

            tokens = _issue_tokens(int(new_user.id))
            return _envelope_ok({"user": _serialize_user(new_user), "tokens": tokens}, status=201)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_register failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/auth/refresh")
    def mobile_refresh():
        try:
            payload = request.get_json(silent=True) or {}
            refresh_token = (payload.get("refresh_token") or "").strip()
            if not refresh_token:
                return _envelope_error("refresh_token обязателен", code="validation_error", status=400)

            user_id = _refresh_tokens.get(refresh_token)
            if not user_id:
                return _envelope_error("Refresh-токен недействителен", code="invalid_refresh", status=401)

            user = db.session.get(User, int(user_id))
            if not user:
                _revoke_tokens(refresh_token=refresh_token)
                return _envelope_error("Пользователь не найден", code="user_not_found", status=401)

            _revoke_tokens(refresh_token=refresh_token)
            tokens = _issue_tokens(int(user.id))
            return _envelope_ok({"user": _serialize_user(user), "tokens": tokens})
        except Exception:
            current_app.logger.exception("mobile_refresh failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/auth/logout")
    @_with_mobile_user
    def mobile_logout(user: User, access_token: str):
        payload = request.get_json(silent=True) or {}
        refresh_token = (payload.get("refresh_token") or "").strip() or None
        _revoke_tokens(access_token=access_token, refresh_token=refresh_token)
        return _envelope_ok({})

    @app.get("/api/mobile/v1/auth/me")
    @_with_mobile_user
    def mobile_me(user: User, access_token: str):
        return _envelope_ok(_serialize_user(user))

    @app.get("/api/mobile/v1/profile")
    @_with_mobile_user
    def mobile_profile(user: User, access_token: str):
        return _envelope_ok(_serialize_user(user))

    @app.patch("/api/mobile/v1/profile")
    @_with_mobile_user
    def mobile_update_profile(user: User, access_token: str):
        try:
            payload = request.get_json(silent=True) or {}
            username = (payload.get("username") or "").strip()
            raw_email = payload.get("email") or ""
            email = normalize_email(raw_email)
            current_password = payload.get("current_password") or ""

            if not check_password_hash(user.password_hash, current_password):
                return _envelope_error("Для изменения профиля укажите текущий пароль.", code="invalid_password", status=400)

            username_error = _validate_username(username)
            if username_error:
                return _envelope_error(username_error, code="validation_error", status=400)

            if not raw_email.strip() or not email:
                return _envelope_error("Введите корректный email.", code="validation_error", status=400)

            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user.id:
                return _envelope_error("Пользователь с таким именем уже существует", code="user_exists", status=400)

            existing_contact = UserContact.query.filter_by(email=email).first()
            if existing_contact and existing_contact.user_id != user.id:
                return _envelope_error("Этот email уже используется другим аккаунтом.", code="email_exists", status=400)

            user.username = username
            if user.contact is None:
                user.contact = UserContact(email=email)
            else:
                user.contact.email = email

            db.session.commit()
            return _envelope_ok(_serialize_user(user))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_update_profile failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/profile/password/send-code")
    @_with_mobile_user
    def mobile_send_password_code(user: User, access_token: str):
        try:
            destination = (user.contact.email if user.contact and user.contact.email else "").strip()
            if not destination:
                return _envelope_error("Сначала укажите email в профиле.", code="no_email", status=400)

            if _rate_limited("mobile_profile_password_send", limit=8, window_seconds=15 * 60, identity=str(user.id)):
                return _envelope_error("Слишком много попыток. Попробуйте позже.", code="rate_limited", status=429)

            sent, code = _issue_reset_code(user.id, destination)
            data = {"sent": sent}
            if not sent and current_app.debug:
                data["dev_code"] = code

            return _envelope_ok(data)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_send_password_code failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/profile/password/change")
    @_with_mobile_user
    def mobile_change_password(user: User, access_token: str):
        try:
            payload = request.get_json(silent=True) or {}
            code = (payload.get("code") or "").strip()
            new_password = payload.get("new_password") or ""

            if not (code.isdigit() and len(code) == 6):
                return _envelope_error("Код должен состоять из 6 цифр.", code="validation_error", status=400)

            destination = (user.contact.email if user.contact and user.contact.email else "").strip()
            if not destination:
                return _envelope_error("Сначала укажите email в профиле.", code="no_email", status=400)

            token = _get_active_reset_token(user.id, destination)
            if not token:
                return _envelope_error("Код не найден или истек. Запросите новый.", code="code_expired", status=400)

            max_attempts = max(3, int(current_app.config.get("PASSWORD_RESET_MAX_ATTEMPTS", 5)))
            if token.attempts >= max_attempts:
                return _envelope_error("Превышено число попыток. Запросите новый код.", code="too_many_attempts", status=400)

            if not check_password_hash(token.code_hash, code):
                token.attempts += 1
                db.session.commit()
                return _envelope_error("Неверный код подтверждения.", code="invalid_code", status=400)

            password_error = _validate_password_strength(new_password, username=user.username)
            if password_error:
                return _envelope_error(password_error, code="validation_error", status=400)

            if check_password_hash(user.password_hash, new_password):
                return _envelope_error("Новый пароль должен отличаться от текущего.", code="same_password", status=400)

            now = datetime.utcnow()
            user.password_hash = generate_password_hash(new_password, method="scrypt")
            token.used_at = now
            PasswordResetToken.query.filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
                PasswordResetToken.id != token.id,
            ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
            db.session.commit()

            return _envelope_ok({"changed": True})
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_change_password failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/upload")
    def mobile_upload_image():
        try:
            if _rate_limited("mobile_upload", limit=40, window_seconds=10 * 60):
                return _envelope_error("Слишком много загрузок. Попробуйте позже.", code="rate_limited", status=429)

            if "image" not in request.files:
                return _envelope_error("Файл не был загружен", code="validation_error", status=400)

            file = request.files["image"]
            if file.filename == "":
                return _envelope_error("Файл не выбран", code="validation_error", status=400)

            if not _allowed_file(file.filename):
                return _envelope_error("Недопустимый тип файла", code="validation_error", status=400)

            extension, validation_error = _validate_uploaded_image(file)
            if validation_error is not None:
                return _envelope_error(validation_error, code="validation_error", status=400)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:12]}.{extension}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
            file.save(filepath)

            color_count = _clamp_color_count(request.form.get("color_count", 5, type=int))

            try:
                palette = extract_colors_from_image(filepath, color_count)
            except Exception:
                current_app.logger.exception("mobile_upload_image: extract failed")
                return _envelope_error("Не удалось извлечь цвета из изображения", code="extract_failed", status=500)

            mobile_user = _current_mobile_user_optional()
            upload_record = Upload(
                filename=unique_filename,
                user_id=mobile_user.id if mobile_user else None,
            )
            db.session.add(upload_record)
            db.session.commit()

            return _envelope_ok(
                {
                    "filename": unique_filename,
                    "palette": palette,
                }
            )
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_upload_image failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.post("/api/mobile/v1/export")
    def mobile_export_palette():
        try:
            if _rate_limited("mobile_export", limit=120, window_seconds=10 * 60):
                return _envelope_error("Слишком много экспортов. Попробуйте позже.", code="rate_limited", status=429)

            payload = request.get_json(silent=True) or {}
            colors = _normalize_palette_colors(payload.get("colors", []))
            if not colors:
                return _envelope_error("Не переданы корректные цвета палитры", code="validation_error", status=400)

            format_type = (request.args.get("format") or "json").lower()
            content, filename, mode = export_palette_data(colors, format_type)
            if content is None or filename is None:
                return _envelope_error("Неподдерживаемый формат экспорта", code="unsupported_format", status=400)

            suffix = f".{format_type}"
            with tempfile.NamedTemporaryFile(delete=False, mode=mode, suffix=suffix) as f:
                if isinstance(content, str):
                    f.write(content)
                else:
                    f.write(content)
                temp_path = f.name

            response = send_file(temp_path, as_attachment=True, download_name=filename)

            @response.call_on_close
            def cleanup():
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            return response
        except Exception:
            current_app.logger.exception("mobile_export_palette failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.get("/api/mobile/v1/palettes")
    @_with_mobile_user
    def mobile_get_palettes(user: User, access_token: str):
        try:
            limit = max(1, min(int(request.args.get("limit", 50)), 200))
            offset = max(0, int(request.args.get("offset", 0)))
        except ValueError:
            return _envelope_error("Некорректные limit/offset", code="validation_error", status=400)

        sort = (request.args.get("sort") or "created_desc").strip().lower()
        query = Palette.query.filter_by(user_id=user.id)

        if sort == "created_asc":
            query = query.order_by(Palette.created_at.asc())
        elif sort == "name_asc":
            query = query.order_by(Palette.name.asc())
        elif sort == "name_desc":
            query = query.order_by(Palette.name.desc())
        else:
            query = query.order_by(Palette.created_at.desc())

        total = query.count()
        items = query.offset(offset).limit(limit).all()

        return _envelope_ok(
            {
                "items": [_serialize_palette(item) for item in items],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )

    @app.post("/api/mobile/v1/palettes")
    @_with_mobile_user
    def mobile_create_palette(user: User, access_token: str):
        try:
            payload = request.get_json(silent=True) or {}
            raw_name = payload.get("name")
            name = (raw_name or "").strip()
            colors = _normalize_palette_colors(payload.get("colors", []))

            if colors is None:
                return _envelope_error(
                    "Палитра должна содержать от 3 до 15 корректных HEX-цветов",
                    code="validation_error",
                    status=400,
                )

            if raw_name is not None and str(raw_name).strip() == "":
                return _envelope_error("Название палитры не может быть пустым", code="validation_error", status=400)

            if not name:
                base = "Моя палитра"
                candidate = base
                index = 1
                while Palette.query.filter_by(user_id=user.id, name=candidate).first() is not None:
                    candidate = f"{base} {index}"
                    index += 1
                name = candidate
            else:
                existing = Palette.query.filter_by(user_id=user.id, name=name).first()
                if existing is not None:
                    return _envelope_error("У вас уже есть палитра с таким названием", code="name_exists", status=400)

            palette = Palette(name=name, colors=colors, user_id=user.id)
            db.session.add(palette)
            db.session.commit()

            return _envelope_ok(_serialize_palette(palette), status=201)
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_create_palette failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.patch("/api/mobile/v1/palettes/<int:palette_id>")
    @_with_mobile_user
    def mobile_rename_palette(user: User, access_token: str, palette_id: int):
        try:
            payload = request.get_json(silent=True) or {}
            name = (payload.get("name") or "").strip()
            if not name:
                return _envelope_error("Название палитры не может быть пустым", code="validation_error", status=400)

            palette = db.session.get(Palette, palette_id)
            if palette is None:
                return _envelope_error("Палитра не найдена", code="not_found", status=404)
            if palette.user_id != user.id:
                return _envelope_error("У вас нет прав на изменение этой палитры", code="forbidden", status=403)

            existing = Palette.query.filter_by(user_id=user.id, name=name).first()
            if existing and existing.id != palette.id:
                return _envelope_error("У вас уже есть палитра с таким названием", code="name_exists", status=400)

            palette.name = name
            db.session.commit()
            return _envelope_ok(_serialize_palette(palette))
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_rename_palette failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)

    @app.delete("/api/mobile/v1/palettes/<int:palette_id>")
    @_with_mobile_user
    def mobile_delete_palette(user: User, access_token: str, palette_id: int):
        try:
            palette = db.session.get(Palette, palette_id)
            if palette is None:
                return _envelope_error("Палитра не найдена", code="not_found", status=404)
            if palette.user_id != user.id:
                return _envelope_error("У вас нет прав на удаление этой палитры", code="forbidden", status=403)

            db.session.delete(palette)
            db.session.commit()
            return _envelope_ok({})
        except Exception:
            db.session.rollback()
            current_app.logger.exception("mobile_delete_palette failed")
            return _envelope_error("Внутренняя ошибка сервера", code="server_error", status=500)
