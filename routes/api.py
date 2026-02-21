"""
Программа: «Paleta» – веб-приложение для генерации и экспорта цветовых палитр.
Модуль: routes/api.py – REST-подобные API-маршруты.
"""

import os
import tempfile
import uuid
from datetime import datetime

from flask import current_app, jsonify, request, send_file, send_from_directory, session
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from config import Config
from extensions import db
from flask_babel import gettext as _
from models.palette import Palette
from models.upload import Upload
from utils.export_handler import export_palette_data
from utils.image_processor import extract_colors_from_image
from utils.palette_service import (
    PaletteValidationError,
    clamp_color_count,
    normalize_palette_colors,
    resolve_palette_name,
    validate_uploaded_image,
)
from utils.rate_limit import get_client_identifier

def _allowed_file(filename: str) -> bool:
    return Config.allowed_file(filename)


def _api_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _rate_limited(bucket: str, limit: int, window_seconds: int, identity: str | None = None) -> bool:
    limiter = current_app.extensions.get("rate_limiter")
    if limiter is None:
        return False

    rate_identity = identity or get_client_identifier()
    rate_key = f"{bucket}:{rate_identity}"
    return not limiter.is_allowed(rate_key, limit, window_seconds)


def _clamp_color_count(raw_value: int | None) -> int:
    return clamp_color_count(raw_value, Config.MIN_COLOR_COUNT, Config.MAX_COLOR_COUNT)


def _validate_uploaded_image(file_storage):
    try:
        return (
            validate_uploaded_image(
                file_storage,
                allowed_formats=Config.ALLOWED_IMAGE_FORMATS,
                max_pixels=Config.MAX_IMAGE_PIXELS,
            ),
            None,
        )
    except PaletteValidationError as exc:
        return None, _api_error(_(exc.message), exc.status)


def _normalize_palette_colors(colors):
    return normalize_palette_colors(colors, Config.MIN_COLOR_COUNT, Config.MAX_COLOR_COUNT)


def register_routes(app):
    @app.route("/api/upload", methods=["POST"])
    def upload_image():
        """Обработчик загрузки изображения и извлечения палитры."""
        try:
            if _rate_limited("upload", limit=40, window_seconds=10 * 60):
                return _api_error(_("Слишком много загрузок. Попробуйте позже."), 429)

            if "image" not in request.files:
                return _api_error(_("Файл не был загружен"), 400)

            file = request.files["image"]

            if file.filename == "":
                return _api_error(_("Файл не выбран"), 400)

            if not _allowed_file(file.filename):
                return _api_error(_("Недопустимый тип файла"), 400)

            extension, validation_error = _validate_uploaded_image(file)
            if validation_error is not None:
                return validation_error

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{uuid.uuid4().hex[:12]}.{extension}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)

            file.save(filepath)

            color_count = _clamp_color_count(request.form.get("color_count", 5, type=int))

            try:
                palette = extract_colors_from_image(filepath, color_count)
            except Exception:
                current_app.logger.exception("Ошибка извлечения цветов из изображения")
                return _api_error(_("Не удалось извлечь цвета из изображения"), 500)

            upload_record = Upload(
                filename=unique_filename,
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(upload_record)
            db.session.commit()

            session["last_upload"] = {
                "filename": unique_filename,
                "palette": palette,
            }

            return jsonify(
                {
                    "success": True,
                    "filename": unique_filename,
                    "palette": palette,
                }
            )

        except Exception:
            current_app.logger.exception("Критическая ошибка обработки загрузки")
            return _api_error(_("Внутренняя ошибка сервера"), 500)

    @app.route("/api/palettes/save", methods=["POST"])
    @login_required
    def save_palette():
        try:
            if _rate_limited(f"palette_save:user:{current_user.id}", limit=60, window_seconds=10 * 60):
                return _api_error(_("Слишком много запросов. Попробуйте позже."), 429)

            data = request.get_json(force=True)
            requested_name = data.get("name")
            colors = _normalize_palette_colors(data.get("colors", []))

            if not colors:
                return _api_error(_("Палитра должна содержать корректные HEX-цвета"), 400)

            default_base_name = _("Моя палитра")
            default_names = {
                default_base_name,
                _("Без названия"),
                "Untitled Palette",
                "Random Palette",
                "",
            }

            try:
                palette_name = resolve_palette_name(
                    user_id=current_user.id,
                    requested_name=requested_name,
                    default_base_name=default_base_name,
                    default_names=default_names,
                )
            except PaletteValidationError as exc:
                return _api_error(_(exc.message), exc.status)

            existing_palette = Palette.query.filter_by(
                user_id=current_user.id,
                name=palette_name,
            ).first()
            if existing_palette:
                return _api_error(_("У вас уже есть палитра с таким названием"), 400)

            new_palette = Palette(
                name=palette_name,
                colors=colors,
                user_id=current_user.id,
            )
            db.session.add(new_palette)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return _api_error(_("У вас уже есть палитра с таким названием"), 400)

            return jsonify({"success": True, "palette_id": new_palette.id})

        except Exception:
            current_app.logger.exception("Ошибка сохранения палитры")
            return _api_error(_("Внутренняя ошибка сервера"), 500)

    @app.route("/api/palettes/rename/<int:palette_id>", methods=["POST"])
    @login_required
    def rename_palette(palette_id: int):
        """Переименовать существующую палитру текущего пользователя."""
        try:
            if _rate_limited(f"palette_rename:user:{current_user.id}", limit=80, window_seconds=10 * 60):
                return _api_error(_("Слишком много запросов. Попробуйте позже."), 429)

            data = request.get_json(force=True)
            new_name = (data.get("name") or "").strip()

            if not new_name:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": _("Название палитры не может быть пустым"),
                        }
                    ),
                    400,
                )

            palette = Palette.query.get_or_404(palette_id)

            if palette.user_id != current_user.id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": _("У вас нет прав на изменение этой палитры"),
                        }
                    ),
                    403,
                )

            existing = Palette.query.filter_by(
                user_id=current_user.id,
                name=new_name,
            ).first()
            if existing and existing.id != palette.id:
                return _api_error(_("У вас уже есть палитра с таким названием"), 400)

            palette.name = new_name
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return _api_error(_("У вас уже есть палитра с таким названием"), 400)

            return jsonify({"success": True})

        except Exception:
            current_app.logger.exception("Ошибка переименования палитры")
            return _api_error(_("Внутренняя ошибка сервера"), 500)

    @app.route("/api/palettes/delete/<int:palette_id>", methods=["DELETE"])
    @login_required
    def delete_palette(palette_id: int):
        try:
            if _rate_limited(f"palette_delete:user:{current_user.id}", limit=60, window_seconds=10 * 60):
                return _api_error(_("Слишком много запросов. Попробуйте позже."), 429)

            palette = Palette.query.get_or_404(palette_id)

            if palette.user_id != current_user.id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": _("У вас нет прав на удаление этой палитры"),
                        }
                    ),
                    403,
                )

            db.session.delete(palette)
            db.session.commit()

            return jsonify({"success": True})

        except Exception:
            current_app.logger.exception("Ошибка удаления палитры")
            return _api_error(_("Внутренняя ошибка сервера"), 500)

    @app.route("/api/export", methods=["POST"])
    def export_palette():
        try:
            if _rate_limited("export", limit=120, window_seconds=10 * 60):
                return _api_error(_("Слишком много экспортов. Попробуйте позже."), 429)

            data = request.get_json(force=True)
            colors = _normalize_palette_colors(data.get("colors", []))

            format_type = request.args.get("format", "json").lower()

            if not colors:
                return _api_error(_("Не переданы корректные цвета палитры"), 400)

            content, filename, mode = export_palette_data(colors, format_type)
            if content is None or filename is None:
                if format_type == "png":
                    return jsonify(
                        {
                            "success": True,
                            "message": _("Экспорт PNG пока не реализован"),
                        }
                    )
                return _api_error(_("Неподдерживаемый формат экспорта"), 400)

            suffix = f".{format_type}"
            with tempfile.NamedTemporaryFile(
                delete=False,
                mode=mode,
                suffix=suffix,
            ) as f:
                f.write(content)
                temp_path = f.name

            response = send_file(temp_path, as_attachment=True, download_name=filename)

            @response.call_on_close
            def cleanup():
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            return response

        except Exception:
            current_app.logger.exception("Ошибка экспорта палитры")
            return _api_error(_("Внутренняя ошибка сервера"), 500)

    @app.route("/static/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/favicon.ico")
    def favicon():
        return "", 204
