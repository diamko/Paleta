"""
Программа: «Paleta» – веб-приложение для работы с цветовыми палитрами.
Модуль: models/palette.py – модель цветовой палитры.

Назначение модуля:
- Описание ORM-модели Palette для хранения пользовательских палитр.
- Хранение названия палитры, списка цветов и привязки к пользователю.
- Дополнительный метод для экспорта палитры в формат GPL (GIMP Palette).
"""

from datetime import datetime, timezone

from extensions import db


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Palette(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Без названия")
    colors = db.Column(db.JSON, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_palette_user_name"),
    )

    def to_gpl_format(self):
        gpl = f"GIMP Palette\nName: {self.name}\n#\n"
        for color in self.colors:
            hex_color = color.lstrip("#")
            rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            gpl += f"{rgb[0]} {rgb[1]} {rgb[2]} Color\n"
        return gpl
