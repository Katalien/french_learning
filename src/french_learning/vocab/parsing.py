"""Разбор списка слов в мягком формате (FR-021, FR-022; research R6).

Строка: «французское — перевод[, перевод…]». Разделитель — первое « — », « – », « - »
или табуляция. Необязательно: артикль le / la / l' / les / un / une / des (можно через
запятую: «la, pomme - яблоко»; неопределённый переводится в определённый), пометки (m) (f)
(v) (adj) (phr) (nom) (adv) (prep) (pron). Фраза — если есть ? или !, строка начинается
с заглавной буквы или в ней 4 слова и больше, либо пометка (phr).
Пустые строки и строки с # пропускаются.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEPARATORS = (" — ", " – ", " - ", "\t")
_MARKER = re.compile(r"\((m|f|v|adj|phr|nom|adv|prep|pron)\)", re.IGNORECASE)
_ARTICLE = re.compile(r"^(les|le|la|une|un|des)(?:\s*,\s*|\s+)|^(l)['’]\s*,?\s*", re.IGNORECASE)
_VOWELS = "aeiouyàâäéèêëîïôöùûüœæ"
_GENDER = {"le": "m", "la": "f", "un": "m", "une": "f"}
_POS = {"v": "verbe", "adj": "adj", "nom": "nom", "adv": "adv", "prep": "prep", "pron": "pron"}


@dataclass
class ParsedLine:
    line_no: int
    raw: str
    text: str
    translations: list[str]
    article: str | None = None
    gender: str | None = None
    entry_type: str = "word"
    pos: str | None = None
    needs_completion: bool = True


@dataclass
class Unrecognized:
    line_no: int
    raw: str
    reason: str


@dataclass
class ParseResult:
    entries: list[ParsedLine] = field(default_factory=list)
    unrecognized: list[Unrecognized] = field(default_factory=list)


def _split(line: str) -> tuple[str, str] | None:
    positions = [(line.find(sep), sep) for sep in SEPARATORS if sep in line]
    if not positions:
        return None
    index, sep = min(positions)
    return line[:index], line[index + len(sep) :]


def _is_phrase(text: str) -> bool:
    return bool(re.search(r"[?!]", text)) or text[:1].isupper() or len(text.split()) >= 4


def _definite(article: str, text: str) -> str | None:
    """Определённый артикль; перед «h» не угадываем (h muet или h aspiré) — дополнит агент."""
    if article in ("un", "une"):
        first = text[:1].lower()
        if first == "h":
            return None
        if first in _VOWELS:
            return "l'"
        return "le" if article == "un" else "la"
    return {"des": "les"}.get(article, article)


def parse_line(line_no: int, raw: str) -> ParsedLine | Unrecognized:
    parts = _split(raw.strip())
    if parts is None:
        return Unrecognized(line_no, raw, "нет разделителя «—» между словом и переводом")
    left, right = parts
    if _split(right) is not None:
        return Unrecognized(line_no, raw, "несколько разделителей — неясно, где перевод")
    translations = [t.strip() for t in re.split(r"[,;]", right) if t.strip()]
    if not translations:
        return Unrecognized(line_no, raw, "нет перевода")

    markers = {m.lower() for m in _MARKER.findall(left)}
    text = _MARKER.sub("", left).strip()
    if not text:
        return Unrecognized(line_no, raw, "нет французского слова")

    entry = ParsedLine(line_no, raw, text, translations)
    if "phr" in markers or ("v" not in markers and _is_phrase(text)):
        entry.entry_type = "phrase"
        entry.needs_completion = False
        return entry

    match = _ARTICLE.match(text)
    if match:
        article = (match.group(1) or "l'").lower()
        entry.text = text[match.end() :].strip()
        entry.gender = _GENDER.get(article)
        entry.article = _definite(article, entry.text)
        entry.pos = "nom"
    if "m" in markers:
        entry.gender = "m"
    if "f" in markers:
        entry.gender = "f"
    for marker, pos in _POS.items():
        if marker in markers:
            entry.pos = pos
    if "v" in markers:
        entry.entry_type = "verb"
    return entry


def parse_word_list(text: str) -> ParseResult:
    result = ParseResult()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parsed = parse_line(line_no, raw)
        if isinstance(parsed, Unrecognized):
            result.unrecognized.append(parsed)
        else:
            result.entries.append(parsed)
    return result
