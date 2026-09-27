"""Шаблоны Jinja2 и вспомогательные функции для них."""

from __future__ import annotations

import datetime as dt
from pathlib import Path, PurePosixPath

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from french_learning.content.render import headings, render_markdown
from french_learning.content.schema import EXERCISE_TYPE_NAMES, GAP_RE
from french_learning.exercises.grading import correct_answers
from french_learning.vocab.entries import display_fr

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


def markdown(text: str | None, path: str | None = None, anchors: str | None = None) -> Markup:
    return Markup(render_markdown(text or "", element_image_base(path), heading_prefix=anchors))


def toc(text: str | None) -> list[tuple[int, str]]:
    """Оглавление теории: только если заголовков 3 и больше (spec, Edge Cases)."""
    found = headings(text or "")
    return found if len(found) >= 3 else []


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


def gap_parts(text: str) -> list[tuple[str, str]]:
    """Текст пункта → части («text», кусок) и («gap», номер) для полей ответа (004)."""
    parts = GAP_RE.split(text)
    return [("text" if i % 2 == 0 else "gap", part) for i, part in enumerate(parts) if part]


def media_path(materials_dir: Path | None, relative: str) -> str:
    """Полный путь к медиафайлу в папке исходных материалов (research R10)."""
    parts = PurePosixPath(relative).parts
    return str(Path(materials_dir, *parts)) if materials_dir else str(PurePosixPath(relative))


STATIC_DIR = Path(__file__).parent / "static"


def asset_version(relative: str) -> str:
    """Версия статического файла для адреса: браузер загрузит новую копию после изменения."""
    try:
        return str((STATIC_DIR / relative).stat().st_mtime_ns)
    except OSError:
        return "0"


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        word = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = few
    else:
        word = many
    return f"{n} {word}"


env = templates.env
env.filters.update(ru_date=ru_date, markdown=markdown, gaps=gaps, toc=toc, gap_parts=gap_parts)
env.globals.update(
    PART_NAMES=PART_NAMES,
    STATUS_NAMES=STATUS_NAMES,
    KIND_NAMES=KIND_NAMES,
    ORIGIN_NAMES=ORIGIN_NAMES,
    EXERCISE_TYPE_NAMES=EXERCISE_TYPE_NAMES,
    plural=plural,
    media_path=media_path,
    asset_version=asset_version,
    display_fr=display_fr,
    correct_answers=correct_answers,
)
