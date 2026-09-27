"""Поиск существующих слов, чтобы не создавать дубли (FR-021; research R9)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml
from pydantic import ValidationError

from french_learning.agent.staging import op_dir
from french_learning.content.loader import load_content
from french_learning.content.schema import VocabEntry


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold().strip())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _staged_entries(root: Path) -> list[VocabEntry]:
    entries = []
    staging = root / ".staging"
    for path in staging.glob("*/vocabulary/*.yaml") if staging.is_dir() else []:
        try:
            entries.append(VocabEntry.model_validate(yaml.safe_load(path.read_text("utf-8"))))
        except (yaml.YAMLError, ValidationError, TypeError):
            continue
    return entries


def vocab_find(
    root: Path, text: str, pos: str | None = None, gender: str | None = None
) -> list[dict]:
    wanted = _normalize(text)
    stored = [e for e in load_content(root).elements.values() if e.kind == "vocab"]
    staged = _staged_entries(root)
    hits = []
    for entry, is_staged in [(e, False) for e in stored] + [(e, True) for e in staged]:
        if _normalize(entry.text) != wanted:
            continue
        if pos and entry.pos != pos:
            continue
        if gender and entry.gender != gender:
            continue
        hits.append(
            {
                "id": entry.id,
                "text": entry.text,
                "article": entry.article,
                "gender": entry.gender,
                "pos": entry.pos,
                "entry_type": entry.entry_type,
                "translations": [t.text for t in entry.translations],
                "lessons": entry.lessons,
                "exact": entry.text.casefold() == text.casefold().strip(),
                "staged": is_staged,
            }
        )
    return hits


__all__ = ["op_dir", "vocab_find"]
