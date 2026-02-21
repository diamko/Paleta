"""
Программа: «Paleta» – веб-приложение для работы с цветовыми палитрами.
Модуль: models/upload.py – модель загруженного изображения.

Назначение модуля:
- Описание ORM-модели Upload для учёта загруженных пользователями изображений.
- Хранение имени файла, даты загрузки и (при наличии) ссылки на пользователя.
"""

from datetime import datetime, timezone
from extensions import db


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=_utcnow)
    # Привязка к пользователю (может быть пустой для анонимных загрузок)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
