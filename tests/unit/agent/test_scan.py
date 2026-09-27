"""Опись папки урока (US1: FR-002, FR-005; US4: FR-040, FR-040a; research R7, R8)."""

import datetime as dt
import os
from pathlib import Path

import pytest
import yaml

from french_learning.agent.scan import ScanError, scan_lesson, sha256_file


def by_name(result):
    return {Path(f.path).name: f for f in result.files}


def test_lesson_number_parts_types_hashes(materials: Path, store: Path):
    result = scan_lesson(materials / "Leçon 07", materials_root=materials, content_root=store)
    assert result.lesson == 7
    files = by_name(result)
    assert files["IMG_0001.jpeg"].part == "class"
    assert files["IMG_0101.jpeg"].part == "homework"
    assert files["IMG_0101.jpeg"].path == "Leçon 07/Devoirs/IMG_0101.jpeg"
    kinds = {name: f.kind for name, f in files.items()}
    assert kinds["regles.pdf"] == "pdf"
    assert kinds["avoir.docx"] == "docx"
    assert kinds["audio.mp3"] == "audio"
    assert kinds["notes.xyz"] == "other"
    assert kinds["IMG_0002.jpeg"] == "image"
    assert files["regles.pdf"].sha256 == sha256_file(materials / "Leçon 07/regles.pdf")


def test_exif_date_and_suggested_date(materials: Path, store: Path):
    for path in (materials / "Leçon 07").rglob("*"):
        if path.is_file():
            stamp = dt.datetime(2026, 9, 10, 12).timestamp()
            os.utime(path, (stamp, stamp))
    result = scan_lesson(materials / "Leçon 07", materials_root=materials, content_root=store)
    files = by_name(result)
    assert files["IMG_0001.jpeg"].date == "2026-09-05"  # EXIF DateTimeOriginal
    assert files["IMG_0002.jpeg"].date == "2026-09-10"  # время изменения
    assert result.suggested_date == "2026-09-05"


def test_duplicates_prefer_homework(materials: Path, store: Path):
    files = by_name(
        scan_lesson(materials / "Leçon 07", materials_root=materials, content_root=store)
    )
    assert files["dup.jpeg"].duplicate_of == "Leçon 07/Devoirs/IMG_0101.jpeg"
    assert files["IMG_0101.jpeg"].duplicate_of is None


@pytest.mark.parametrize("folder", ["Leçon XX", "missing"])
def test_bad_folders(materials: Path, store: Path, folder: str):
    if folder == "Leçon XX":
        (materials / folder).mkdir()
        (materials / folder / "a.jpeg").write_bytes(b"x")
    with pytest.raises(ScanError):
        scan_lesson(materials / folder, materials_root=materials, content_root=store)


def test_empty_folder(materials: Path, store: Path):
    (materials / "Leçon 09").mkdir()
    with pytest.raises(ScanError, match="пуст"):
        scan_lesson(materials / "Leçon 09", materials_root=materials, content_root=store)


def test_conflict_with_existing_lesson_from_other_folder(materials: Path, store: Path):
    # В хранилище урок 1 добавлен из папки «Leçon 01»; новая папка «Leçon 1» — тот же номер.
    (materials / "Leçon 07").rename(materials / "Leçon 1")
    result = scan_lesson(materials / "Leçon 1", materials_root=materials, content_root=store)
    assert result.lesson == 1
    assert result.conflict == {"existing_source_folder": "Leçon 01"}


def test_same_folder_is_not_a_conflict(materials: Path, store: Path):
    (materials / "Leçon 07").rename(materials / "Leçon 01")
    result = scan_lesson(materials / "Leçon 01", materials_root=materials, content_root=store)
    assert result.conflict is None
    assert result.existing is True


def write_journal(store: Path, materials: Path, number: int, names: list[str]) -> None:
    folder = f"{number:03d}"
    lesson_dir = store / "lessons" / folder
    lesson_dir.mkdir(parents=True, exist_ok=True)
    lesson = {"id": "les-seventhx", "number": number, "source_folder": f"Leçon {number:02d}"}
    lesson["files"] = [
        {
            "path": f"Leçon {number:02d}/{name}",
            "part": "homework" if name.startswith("Devoirs") else "class",
            "sha256": sha256_file(materials / f"Leçon {number:02d}" / name),
            "classification": "theory",
            "elements": [],
        }
        for name in names
    ]
    (lesson_dir / "lesson.yaml").write_text(yaml.safe_dump(lesson, allow_unicode=True), "utf-8")


def test_journal_states(materials: Path, store: Path):
    """US4: processed / new / changed / missing относительно журнала урока."""
    write_journal(store, materials, 7, ["IMG_0001.jpeg", "IMG_0002.jpeg", "regles.pdf"])
    (materials / "Leçon 07/IMG_0002.jpeg").write_bytes(b"changed")
    (materials / "Leçon 07/regles.pdf").unlink()
    result = scan_lesson(materials / "Leçon 07", materials_root=materials, content_root=store)
    files = by_name(result)
    assert files["IMG_0001.jpeg"].state == "processed"
    assert files["IMG_0002.jpeg"].state == "changed"
    assert files["IMG_0003.jpeg"].state == "new"
    assert result.missing == ["Leçon 07/regles.pdf"]


def test_rescan_without_changes_is_all_processed(materials: Path, store: Path):
    names = [
        p.relative_to(materials / "Leçon 07").as_posix()
        for p in (materials / "Leçon 07").rglob("*")
        if p.is_file()
    ]
    write_journal(store, materials, 7, names)
    result = scan_lesson(materials / "Leçon 07", materials_root=materials, content_root=store)
    assert {f.state for f in result.files} == {"processed"}
