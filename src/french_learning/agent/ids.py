"""Новые уникальные идентификаторы с учётом хранилища и черновика."""

from __future__ import annotations

import re
from pathlib import Path

from french_learning.content.writer import new_id

_ID_IN_FILE = re.compile(r"\b(?:les|th|tx|ex|voc|top|rep)-[a-z2-7]{8}\b")


def existing_ids(root: Path) -> set[str]:
    """Все идентификаторы, встречающиеся в YAML и Markdown хранилища, включая черновик."""
    found: set[str] = set()
    for path in root.rglob("*"):
        if ".git" in path.parts or path.suffix not in {".yaml", ".md"} or not path.is_file():
            continue
        found.update(_ID_IN_FILE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return found


def new_ids(root: Path, prefix: str, count: int) -> list[str]:
    taken = existing_ids(root)
    result: list[str] = []
    while len(result) < count:
        candidate = new_id(prefix)
        if candidate not in taken:
            taken.add(candidate)
            result.append(candidate)
    return result
