"""
Программа: «Paleta» – веб-приложение для генерации и экспорта цветовых палитр.
Модуль: utils/export_handler.py – формирование данных для экспорта палитр.

Назначение модуля:
- Подготовка содержимого палитры в форматах JSON, GPL, ASE, CSV и ACO.
- Возврат бинарных данных, имени файла и режима записи для последующей отправки пользователю.
"""

import json
import struct
from datetime import datetime
from typing import List, Tuple, Optional


def export_palette_data(colors: List[str], format_type: str = "json") -> Tuple[Optional[bytes], Optional[str], str]:
    """Генерирует данные для экспорта палитры в различных форматах.

    Возвращает кортеж (content, filename, mode), где:
    - content — содержимое файла (bytes),
    - filename — имя файла для скачивания,
    - mode — режим открытия временного файла ('w' или 'wb').
    """
    if not colors:
        return None, None, "w"

    content: bytes | str
    filename = ""
    mode = "w"  # по умолчанию текстовый режим

    # Текстовый JSON-файл с описанием палитры
    if format_type == "json":
        content = json.dumps(
            {
                "name": "Цветовая палитра",
                "colors": colors,
                "generated": datetime.now().isoformat(),
            },
            indent=2,
        )
        filename = "palette.json"

    # GPL-палитра для GIMP
    elif format_type == "gpl":
        content = "GIMP Palette\n"
        content += "Name: Generated Palette\n"
        content += "Columns: 5\n#\n"
        for color in colors:
            c = color.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            content += f"{r:3d} {g:3d} {b:3d} #{c.upper()}\n"
        filename = "palette.gpl"

    # ASE-палитра для продуктов Adobe
    elif format_type == "ase":
        content = b"ASEF"
        content += struct.pack(">I", 0x00010000)
        content += struct.pack(">I", len(colors))
        for i, color in enumerate(colors):
            c = color.lstrip("#")
            r, g, b = int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(
                c[4:6], 16
            ) / 255.0
            name = f"Цвет {i+1}"
            name_bytes = name.encode("utf-16-be")
            name_len = len(name_bytes) // 2
            block_data = struct.pack(">H", name_len) + name_bytes
            block_data += b"RGB "
            block_data += struct.pack(">fff", r, g, b)
            block_len = len(block_data)
            content += struct.pack(">HI", 0x0001, block_len)
            content += block_data
        filename = "palette.ase"
        mode = "wb"

    # Простой CSV-файл, по одному HEX-цвету в строке
    elif format_type == "csv":
        content = "Цвет\n"
        for color in colors:
            content += f"{color}\n"
        filename = "palette.csv"

    # ACO-палитра для Adobe Photoshop
    elif format_type == "aco":
        version = 1
        count = len(colors)
        content = struct.pack(">HH", version, count)
        for color in colors:
            c = color.lstrip("#")
            r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            content += struct.pack(">HHHH", 0, r * 256, g * 256, b * 256)
        filename = "palette.aco"
        mode = "wb"

    elif format_type == "png":
        # Пока не реализовано
        return None, None, "w"

    else:
        return None, None, "w"

    # Приводим к bytes для удобства записи
    if isinstance(content, str) and mode == "w":
        return content.encode("utf-8"), filename, "wb"

    return content, filename, mode
