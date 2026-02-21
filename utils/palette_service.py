import re

from PIL import Image, UnidentifiedImageError

from models.palette import Palette


class PaletteValidationError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def clamp_color_count(raw_value: int | None, min_count: int, max_count: int) -> int:
    if raw_value is None:
        return 5
    return max(min_count, min(max_count, raw_value))


def validate_uploaded_image(file_storage, allowed_formats: set[str], max_pixels: int) -> str:
    file_storage.stream.seek(0)
    try:
        with Image.open(file_storage.stream) as image:
            image.verify()
    except (UnidentifiedImageError, OSError):
        raise PaletteValidationError("VALIDATION_ERROR", "Файл не является корректным изображением")
    finally:
        file_storage.stream.seek(0)

    try:
        with Image.open(file_storage.stream) as image:
            image_format = (image.format or "").lower()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        raise PaletteValidationError("VALIDATION_ERROR", "Файл не является корректным изображением")
    finally:
        file_storage.stream.seek(0)

    if image_format not in allowed_formats:
        raise PaletteValidationError("VALIDATION_ERROR", "Недопустимый формат изображения")

    if width * height > max_pixels:
        raise PaletteValidationError("VALIDATION_ERROR", "Изображение слишком большое по разрешению")

    format_to_extension = {"jpeg": "jpg", "png": "png", "webp": "webp"}
    return format_to_extension[image_format]


def normalize_palette_colors(colors, min_count: int, max_count: int):
    if not isinstance(colors, list):
        return None

    if not (min_count <= len(colors) <= max_count):
        return None

    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    normalized = []
    for raw_color in colors:
        if not isinstance(raw_color, str):
            return None
        color = raw_color.strip()
        if not hex_pattern.match(color):
            return None
        normalized.append(color.upper())
    return normalized


def resolve_palette_name(
    *,
    user_id: int,
    requested_name: str | None,
    default_base_name: str,
    default_names: set[str],
) -> str:
    normalized = (requested_name or "").strip()

    if requested_name is not None and normalized == "":
        raise PaletteValidationError(
            "VALIDATION_ERROR",
            "Название палитры не может быть пустым или состоять только из пробелов",
        )

    if not normalized or normalized in default_names:
        existing_base = Palette.query.filter_by(user_id=user_id, name=default_base_name).first()
        if not existing_base:
            return default_base_name

        counter = 1
        while True:
            candidate = f"{default_base_name} {counter}"
            exists = Palette.query.filter_by(user_id=user_id, name=candidate).first()
            if not exists:
                return candidate
            counter += 1

    return normalized


def serialize_palette(palette: Palette) -> dict:
    return {
        "id": palette.id,
        "name": palette.name,
        "colors": palette.colors,
        "created_at": palette.created_at.isoformat() if palette.created_at else None,
    }
