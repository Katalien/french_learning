"""Правки контента из интерфейса (research R2).

Каждая операция: атомарная запись файлов (временный файл + замена) → git-коммит в хранилище
контента → попытка отправить коммит на GitHub (резервная копия, конституция VI).
Неудачная отправка не отменяет правку: пользователь видит предупреждение.
"""

from __future__ import annotations

import datetime as dt
import os
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from french_learning.content import schema
from french_learning.content.loader import load_content

_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"
PUSH_TIMEOUT_SECONDS = 20


class WriteError(Exception):
    """Правку выполнить нельзя; сообщение показывается пользователю."""


@dataclass
class WriteResult:
    committed: bool
    pushed: bool
    warning: str | None = None


def new_id(prefix: str) -> str:
    return f"{prefix}-" + "".join(secrets.choice(_ID_ALPHABET) for _ in range(8))


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


class ContentWriter:
    def __init__(self, root: Path, author: tuple[str, str] | None = None) -> None:
        self.root = root
        self.author = author

    # --- чтение и атомарная запись -----------------------------------------------------------

    def _read(self, relative: str) -> tuple[dict, str | None]:
        """Данные файла; для Markdown — (шапка, тело)."""
        text = (self.root / relative).read_text(encoding="utf-8")
        if relative.endswith(".md"):
            head, body = text.lstrip("﻿")[3:].split("\n---", 1)
            return yaml.safe_load(head), body
        return yaml.safe_load(text), None

    def _render(self, relative: str, data: dict, body: str | None) -> str:
        if relative.endswith(".md"):
            return f"---\n{_dump_yaml(data)}---{body}"
        return _dump_yaml(data)

    def _write_all(self, files: dict[str, str]) -> None:
        temps: list[tuple[Path, Path]] = []
        try:
            for relative, text in files.items():
                target = self.root / relative
                temp = target.with_name(target.name + ".tmp")
                temp.write_text(text, encoding="utf-8", newline="\n")
                temps.append((temp, target))
            for temp, target in temps:
                os.replace(temp, target)
        except OSError as exc:
            raise WriteError(f"не удалось сохранить изменения: {exc}") from exc
        finally:
            for temp, _target in temps:
                temp.unlink(missing_ok=True)

    # --- git ---------------------------------------------------------------------------------

    def _git(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
        command = ["git", "-C", str(self.root)]
        if self.author:
            command += ["-c", f"user.name={self.author[0]}", "-c", f"user.email={self.author[1]}"]
        return subprocess.run(
            [*command, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    def commit_paths(self, paths: list[str], message: str) -> WriteResult:
        """Коммит указанных путей (включая удалённые) и попытка отправки."""
        return self._commit(paths, message)

    def _commit(self, paths: list[str], message: str) -> WriteResult:
        if self._git("rev-parse", "--git-dir").returncode != 0:
            return WriteResult(False, False, "хранилище не под git: правка сохранена без истории")
        self._git("add", "-A", "--", *paths)
        commit = self._git("commit", "-m", message)
        if commit.returncode != 0:
            return WriteResult(
                False, False, f"правка сохранена, но коммит не создан: {commit.stderr}"
            )
        if not self._git("remote").stdout.strip():
            return WriteResult(
                True, False, "копия не отправлена: не настроен удалённый репозиторий"
            )
        try:
            push = self._git("push", timeout=PUSH_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return WriteResult(True, False, "копия не отправлена: нет ответа от GitHub")
        if push.returncode != 0:
            return WriteResult(True, False, "копия не отправлена: нет связи с GitHub")
        return WriteResult(True, True)

    def save_files(self, files: dict[str, str], message: str) -> WriteResult:
        """Записать файлы атомарно и закоммитить одним коммитом (с попыткой отправки)."""
        return self._save(files, message)

    def _save(self, files: dict[str, str], message: str) -> WriteResult:
        self._write_all(files)
        return self._commit(list(files), message)

    # --- справочные данные -------------------------------------------------------------------

    def _content(self):
        return load_content(self.root)

    def _element_path(self, element_id: str) -> str:
        path = self._content().element_paths.get(element_id)
        if path is None:
            raise WriteError(f"элемент {element_id} не найден")
        return path

    def _topics_data(self) -> dict:
        path = self.root / "topics.yaml"
        if not path.exists():
            return {"sections": [], "topics": []}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {"sections": [], "topics": []}

    # --- урок --------------------------------------------------------------------------------

    def set_lesson_date(self, number: int, date: dt.date | None) -> WriteResult:
        relative = f"lessons/{number:03d}/lesson.yaml"
        if not (self.root / relative).exists():
            raise WriteError(f"урок {number} не найден")
        data, _ = self._read(relative)
        if date is None:
            data.pop("date", None)
        else:
            data["date"] = date
        label = date.isoformat() if date else "не указана"
        return self._save(
            {relative: self._render(relative, data, None)}, f"Урок {number}: дата {label}"
        )

    # --- темы --------------------------------------------------------------------------------

    def _check_new_name(self, topics: list[dict], name: str, except_id: str | None = None) -> str:
        name = name.strip()
        if not name:
            raise WriteError("название темы не может быть пустым")
        for topic in topics:
            if topic["id"] != except_id and topic["name"].casefold() == name.casefold():
                raise WriteError(f"тема «{topic['name']}» уже есть")
        return name

    def _add_topic(self, data: dict, name: str, section: str) -> dict:
        if section not in {s["id"] for s in data.get("sections", [])}:
            raise WriteError(f"неизвестный раздел {section}")
        topic = {
            "id": new_id("top"),
            "name": self._check_new_name(data["topics"], name),
            "section": section,
        }
        data["topics"].append(topic)
        return topic

    def create_topic(self, name: str, section: str) -> tuple[schema.Topic, WriteResult]:
        data = self._topics_data()
        topic = self._add_topic(data, name, section)
        result = self._save({"topics.yaml": _dump_yaml(data)}, f"Новая тема: {topic['name']}")
        return schema.Topic(**topic), result

    def rename_topic(self, topic_id: str, new_name: str) -> WriteResult:
        data = self._topics_data()
        topic = next((t for t in data["topics"] if t["id"] == topic_id), None)
        if topic is None:
            raise WriteError(f"тема {topic_id} не найдена")
        old = topic["name"]
        topic["name"] = self._check_new_name(data["topics"], new_name, except_id=topic_id)
        return self._save({"topics.yaml": _dump_yaml(data)}, f"Тема «{old}» → «{topic['name']}»")

    def merge_topics(self, source_id: str, target_id: str) -> WriteResult:
        if source_id == target_id:
            raise WriteError("тему нельзя объединить саму с собой")
        data = self._topics_data()
        by_id = {t["id"]: t for t in data["topics"]}
        if source_id not in by_id or target_id not in by_id:
            raise WriteError("тема для объединения не найдена")
        files: dict[str, str] = {}
        content = self._content()
        for element_id, element in content.elements.items():
            if source_id not in element.topics:
                continue
            relative = content.element_paths[element_id]
            meta, body = self._read(relative)
            topics = [target_id if t == source_id else t for t in meta.get("topics", [])]
            meta["topics"] = list(dict.fromkeys(topics))
            files[relative] = self._render(relative, meta, body)
        data["topics"] = [t for t in data["topics"] if t["id"] != source_id]
        files["topics.yaml"] = _dump_yaml(data)
        message = f"Темы «{by_id[source_id]['name']}» и «{by_id[target_id]['name']}» объединены"
        return self._save(files, message)

    def set_element_topics(
        self,
        element_id: str,
        topic_ids: list[str],
        new_topic: tuple[str, str] | None = None,
    ) -> WriteResult:
        relative = self._element_path(element_id)
        topics_data = self._topics_data()
        known = {t["id"] for t in topics_data["topics"]}
        unknown = [t for t in topic_ids if t not in known]
        if unknown:
            raise WriteError(f"неизвестные темы: {', '.join(unknown)}")
        files: dict[str, str] = {}
        ids = list(dict.fromkeys(topic_ids))
        if new_topic and new_topic[0].strip():
            topic = self._add_topic(topics_data, *new_topic)
            ids.append(topic["id"])
            files["topics.yaml"] = _dump_yaml(topics_data)
        if not ids:
            raise WriteError("у элемента должна остаться хотя бы одна тема")
        meta, body = self._read(relative)
        meta["topics"] = ids
        files[relative] = self._render(relative, meta, body)
        return self._save(files, f"Темы элемента {element_id} изменены")

    # --- статус упражнения (функция 004, FR-032) --------------------------------------------

    def set_exercise_status(self, element_id: str, status: str) -> WriteResult:
        if status not in schema.STATUS_VALUES:
            raise WriteError(f"неизвестный статус {status}")
        relative, meta, body, element = self._element(element_id)
        if element.kind != "exercise":
            raise WriteError("статус есть только у упражнений")
        meta["status"] = status
        return self._save(
            {relative: self._render(relative, meta, body)},
            f"Упражнение {element_id}: статус {status}",
        )

    # --- используется функциями проверки и сообщений (US4) ----------------------------------

    def _element(self, element_id: str) -> tuple[str, dict, str | None, Any]:
        content = self._content()
        if element_id not in content.elements:
            raise WriteError(f"элемент {element_id} не найден")
        relative = content.element_paths[element_id]
        meta, body = self._read(relative)
        return relative, meta, body, content.elements[element_id]

    def mark_verified(self, element_id: str, item_id: int | None = None) -> WriteResult:
        """Снять «требует проверки» с элемента или пункта упражнения (FR-041)."""
        relative, meta, body, _element = self._element(element_id)
        if item_id is None:
            meta["needs_review"] = {"flag": False}
            what = f"Элемент {element_id} проверен"
        else:
            item = next((i for i in meta.get("items", []) if i.get("id") == item_id), None)
            if item is None:
                raise WriteError(f"пункт {item_id} не найден")
            item.pop("needs_review", None)
            what = f"Элемент {element_id}, пункт {item_id} проверен"
        return self._save({relative: self._render(relative, meta, body)}, what)

    def create_report(
        self, element_id: str, item_id: int | None, comment: str
    ) -> tuple[schema.Report, WriteResult]:
        """Сообщение об ошибке (FR-042); разбирает агент (функция 002)."""
        if not comment.strip():
            raise WriteError("опишите, что не так")
        self._element(element_id)
        report = schema.Report(
            id=new_id("rep"),
            element=element_id,
            item=item_id,
            comment=comment.strip(),
            created=dt.datetime.now().replace(microsecond=0),
        )
        relative = f"reports/{report.id}.yaml"
        (self.root / "reports").mkdir(exist_ok=True)
        text = _dump_yaml(report.model_dump(mode="json"))
        result = self._save({relative: text}, f"Сообщение об ошибке в {element_id}")
        return report, result

    def delete_files(self, paths: list[str], message: str) -> WriteResult:
        """Удалить файлы контента и закоммитить удаление (с попыткой отправки)."""
        for relative in paths:
            target = (self.root / relative).resolve()
            if not target.is_relative_to(self.root.resolve()):
                raise WriteError(f"путь вне хранилища: {relative}")
            target.unlink(missing_ok=True)
        return self._commit(paths, message)
