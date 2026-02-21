"""
Программа: «Paleta» – веб-приложение для генерации и хранения цветовых палитр.
Модуль: models/password_reset_token.py – одноразовые коды восстановления пароля.
"""

from datetime import datetime

from extensions import db


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    channel = db.Column(db.String(10), nullable=False, index=True)  # email | phone
    destination = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User")
