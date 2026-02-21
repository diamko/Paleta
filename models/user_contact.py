"""
Программа: «Paleta» – веб-приложение для генерации и хранения цветовых палитр.
Модуль: models/user_contact.py – контакты пользователя для восстановления пароля.
"""

from datetime import datetime, timezone

from extensions import db


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    user = db.relationship("User", back_populates="contact")
