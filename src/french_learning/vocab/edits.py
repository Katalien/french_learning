"""Добавление и правка записей словаря (FR-020–FR-022, FR-050; research R7).

Слова — это контент: запись в файлы `vocabulary/*.yaml` через `ContentWriter` (атомарно,
один коммит на операцию, отправка). Объединение с существующей записью — по словарной
форме, виду и роду (правила 002): новые переводы добавляются, а не заменяют прежние.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from french_learning.agent.ids import new_ids
from french_learning.content.loader import load_content
from french_learning.content.writer import ContentWriter, WriteResult, _dump_yaml
from french_learning.vocab.parsing import ParsedLine, Unrecognized, parse_word_list


class VocabError(Exception):
    """Правку выполнить нельзя; сообщение показывается пользователю."""


@dataclass
class ImportReport:
    added: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    unrecognized: list[Unrecognized] = field(default_factory=list)
    result: WriteResult | None = None


class VocabEditor:
    def __init__(self, root: Path, author: tuple[str, str] | None = None) -> None:
        self.root = root
        self.writer = ContentWriter(root, author=author)

    # --- поиск существующей записи -----------------------------------------------------------

    def _existing(self) -> tuple[list[Any], dict[str, str]]:
        content = load_content(self.root)
        entries = [e for e in content.elements.values() if e.kind == "vocab"]
        return entries, content.element_paths

    @staticmethod
    def _same(entry: Any, line: ParsedLine) -> bool:
        if entry.text.casefold() != line.text.casefold() or entry.entry_type != line.entry_type:
            return False
        return entry.gender is None or line.gender is None or entry.gender == line.gender

    # --- добавление --------------------------------------------------------------------------

    def _new_data(
        self, entry_id: str, line: ParsedLine, topics: list[str], lesson: int | None
    ) -> dict:
        data: dict[str, Any] = {
            "id": entry_id,
            "kind": "vocab",
            "entry_type": line.entry_type,
            "text": line.text,
        }
        if line.article:
            data["article"] = line.article
        if line.gender:
            data["gender"] = line.gender
        if line.pos:
            data["pos"] = line.pos
        data["translations"] = [
            {"text": t, **({"lesson": lesson} if lesson else {}), "origin": "user"}
            for t in line.translations
        ]
        if lesson:
            data["lessons"] = [lesson]
        data["topics"] = topics
        data["origin"] = "user"
        data["needs_completion"] = line.needs_completion
        return data

    def _merged_data(self, path: str, line: ParsedLine, lesson: int | None) -> tuple[dict, bool]:
        data = yaml.safe_load((self.root / path).read_text(encoding="utf-8"))
        known = {t["text"].casefold() for t in data.get("translations", [])}
        changed = False
        for text in line.translations:
            if text.casefold() not in known:
                data["translations"].append(
                    {"text": text, **({"lesson": lesson} if lesson else {}), "origin": "user"}
                )
                changed = True
        if lesson and lesson not in data.get("lessons", []):
            data.setdefault("lessons", []).append(lesson)
            changed = True
        return data, changed

    def _apply(
        self, lines: list[ParsedLine], topics: list[str], lesson: int | None
    ) -> tuple[dict, list, list, list]:
        if not topics:
            raise VocabError("выберите тему для новых слов")
        entries, paths = self._existing()
        files: dict[str, str] = {}
        added, merged, ids = [], [], []
        fresh = iter(new_ids(self.root, "voc", len(lines)))
        for line in lines:
            match = next((e for e in entries if self._same(e, line)), None)
            if match is not None:
                data, _changed = self._merged_data(paths[match.id], line, lesson)
                files[paths[match.id]] = _dump_yaml(data)
                merged.append(line.text)
                ids.append(match.id)
                continue
            entry_id = next(fresh)
            files[f"vocabulary/{entry_id}.yaml"] = _dump_yaml(
                self._new_data(entry_id, line, topics, lesson)
            )
            added.append(line.text)
            ids.append(entry_id)
        return files, added, merged, ids

    def add_word(
        self,
        *,
        text: str,
        translations: list[str],
        topics: list[str],
        article: str | None = None,
        gender: str | None = None,
        entry_type: str = "word",
        pos: str | None = None,
        lesson: int | None = None,
    ) -> tuple[str, bool]:
        translations = [t.strip() for t in translations if t.strip()]
        if not text.strip() or not translations:
            raise VocabError("нужны французское слово и хотя бы один перевод")
        gender = gender or {"le": "m", "la": "f"}.get(article or "")
        line = ParsedLine(
            0,
            text,
            text.strip(),
            translations,
            article=article or None,
            gender=gender,
            entry_type=entry_type,
            pos=pos or ("nom" if article else None),
            needs_completion=entry_type != "phrase",
        )
        files, added, _merged, ids = self._apply([line], topics, lesson)
        label = "добавлено" if added else "дополнено"
        self.writer.save_files(files, f"Словарь: {label} «{line.text}»")
        return ids[0], not added

    def import_list(self, text: str, topics: list[str], lesson: int | None) -> ImportReport:
        parsed = parse_word_list(text)
        report = ImportReport(unrecognized=parsed.unrecognized)
        if not parsed.entries:
            return report
        files, report.added, report.merged, _ids = self._apply(parsed.entries, topics, lesson)
        report.result = self.writer.save_files(
            files, f"Словарь: добавлено {len(report.added)}, объединено {len(report.merged)}"
        )
        return report
