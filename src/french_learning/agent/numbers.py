"""Следующий номер упражнения во вкладке и справочник тем для навыков."""

from __future__ import annotations

from pathlib import Path

import yaml

from french_learning.agent.staging import op_dir
from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content


def next_number(root: Path, lesson: int, part: str, op: str) -> int:
    numbers = [
        e.number
        for e in load_content(root).elements.values()
        if e.kind == "exercise" and e.lesson == lesson and e.part == part
    ]
    for path in op_dir(root, op).rglob("*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if (
            isinstance(data, dict)
            and data.get("kind") == "exercise"
            and data.get("lesson") == lesson
            and data.get("part") == part
            and isinstance(data.get("number"), int)
        ):
            numbers.append(data["number"])
    return max(numbers, default=0) + 1


def topics_list(root: Path) -> list[dict]:
    index = ContentIndex(load_content(root))
    return [
        {
            "id": item.topic.id,
            "name": item.topic.name,
            "section": group.section.id,
            "section_name": group.section.name,
            "count": item.count,
        }
        for group in index.topics_by_section()
        for item in group.topics
    ]
