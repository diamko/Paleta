"""
Программа: «Paleta» – веб-приложение для генерации и хранения цветовых палитр.
Модуль: models/user.py – модель пользователя системы.

Назначение модуля:
- Описание ORM-модели User для работы с таблицей пользователей в базе данных.
- Хранение учётных записей (логин, хеш пароля) и связей с палитрами и загрузками.
"""

from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    palettes = db.relationship("Palette", backref="author", lazy=True)
    uploads = db.relationship("Upload", backref="user", lazy=True)
    contact = db.relationship(
        "UserContact",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
