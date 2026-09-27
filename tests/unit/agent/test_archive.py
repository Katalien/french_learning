"""Опись урока и общий указатель (FR-038, FR-039; research R5)."""

from pathlib import Path

import yaml

from french_learning.agent.archive import build_archive


def add_journal(store: Path) -> None:
    path = store / "lessons/002/lesson.yaml"
    lesson = yaml.safe_load(path.read_text(encoding="utf-8"))
    lesson["files"] = [
        {
            "path": "Leçon 02/etre.docx",
            "part": "class",
            "sha256": "a" * 64,
            "classification": "theory",
            "elements": ["th-etreverb", "ex-revision"],
            "stored_as": "lessons/002/sources/etre.docx",
        },
        {
            "path": "Leçon 02/Devoirs/hw.jpeg",
            "part": "homework",
            "sha256": "b" * 64,
            "classification": "exercises",
            "elements": ["ex-hwlessbb"],
        },
        {
            "path": "Leçon 02/Video.mov",
            "part": "class",
            "sha256": "c" * 64,
            "classification": "media",
            "elements": [],
        },
        {
            "path": "Leçon 02/blurry.jpeg",
            "part": "class",
            "sha256": "d" * 64,
            "classification": "unrecognized",
            "elements": [],
            "note": "размытое фото",
        },
    ]
    path.write_text(yaml.safe_dump(lesson, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_lesson_inventory(store: Path):
    add_journal(store)
    build_archive(store)
    text = (store / "lessons/002/inventory.md").read_text(encoding="utf-8")
    assert text.startswith("# Урок 2")
    assert "дата не указана" in text
    assert "Артикли" in text and "Глагол être" in text
    assert "## В классе" in text and "## Домашка" in text
    assert "etre.docx" in text and "th-etreverb" in text
    assert "1 — Глагол être — Спрягать être" in text
    assert "## Аудио и видео" in text and "Video.mov" in text
    assert "## Пропущено" in text and "размытое фото" in text


def test_global_index(store: Path):
    build_archive(store)
    text = (store / "index.md").read_text(encoding="utf-8")
    assert "Урок 1" in text and "Урок 2" in text and "Урок 4" in text
    assert "## Темы" in text
    assert "### Грамматика" in text
    assert "Артикли: уроки 1, 2" in text


def test_rebuild_is_stable(store: Path):
    add_journal(store)
    build_archive(store)
    first = (store / "index.md").read_bytes(), (store / "lessons/002/inventory.md").read_bytes()
    build_archive(store)
    second = (store / "index.md").read_bytes(), (store / "lessons/002/inventory.md").read_bytes()
    assert first == second
