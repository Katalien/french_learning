"""Шаблоны Jinja2 и вспомогательные функции для них."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from french_learning.content.render import render_markdown
from french_learning.content.schema import EXERCISE_TYPE_NAMES, GAP_RE

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

PART_NAMES = {"class": "В классе", "homework": "Домашка"}
STATUS_NAMES = {"main": "основное", "optional": "необязательное", "reserve": "резерв"}
KIND_NAMES = {"theory": "Теория", "text": "Текст", "exercise": "Упражнение", "vocab": "Слово"}
ORIGIN_NAMES = {
    "material": "материал урока",
    "external": "внешний ресурс",
    "user": "добавлено вручную",
    "ai": "создано ИИ",
    "service": "внешний сервис",
}
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]  # fmt: skip


def ru_date(value: dt.date | None) -> str:
    if value is None:
        return "дата не указана"
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def element_image_base(path: str | None) -> str:
    """Папка урока или extra/ для картинок: lessons/001/theory/x.md → lessons/001."""
    if not path:
        return ""
    parts = path.split("/")
    return "/".join(parts[:2]) if parts[0] == "lessons" else parts[0]


def markdown(text: str | None, path: str | None = None) -> Markup:
    return Markup(render_markdown(text or "", element_image_base(path)))


def gaps(text: str) -> Markup:
    """Текст пункта с пропусками {{N}} → пустые поля без ответов (FR-023)."""
    parts = GAP_RE.split(text)
    html = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            html.append(str(escape(part)))
        else:
            html.append(f'<span class="gap" aria-label="пропуск {escape(part)}">&nbsp;</span>')
    return Markup("".join(html))


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        word = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = few
    else:
        word = many
    return f"{n} {word}"


env = templates.env
env.filters.update(ru_date=ru_date, markdown=markdown, gaps=gaps)
env.globals.update(
    PART_NAMES=PART_NAMES,
    STATUS_NAMES=STATUS_NAMES,
    KIND_NAMES=KIND_NAMES,
    ORIGIN_NAMES=ORIGIN_NAMES,
    EXERCISE_TYPE_NAMES=EXERCISE_TYPE_NAMES,
    plural=plural,
)
