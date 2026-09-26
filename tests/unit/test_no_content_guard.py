"""Защита публичного репозитория от попадания учебных материалов (конституция, принцип VI)."""

from pathlib import Path

from scripts.check_no_content import find_violations


def _touch(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_clean_repository_has_no_violations(tmp_path: Path) -> None:
    _touch(tmp_path, "src/french_learning/cli.py")
    _touch(tmp_path, "specs/001/spec.md")
    _touch(tmp_path, "pyproject.toml")

    assert find_violations(tmp_path, tracked=None) == []


def test_media_and_documents_outside_allowed_paths_are_violations(tmp_path: Path) -> None:
    for name in ("photo.jpeg", "lesson.pdf", "theory.docx", "audio.mp3", "video.mov"):
        _touch(tmp_path, f"materials/{name}")

    violations = find_violations(tmp_path, tracked=None)

    assert sorted(p.name for p in violations) == [
        "audio.mp3",
        "lesson.pdf",
        "photo.jpeg",
        "theory.docx",
        "video.mov",
    ]


def test_content_storage_layout_is_a_violation(tmp_path: Path) -> None:
    _touch(tmp_path, "lessons/014/lesson.yaml")
    _touch(tmp_path, "vocabulary/voc-abcdefgh.yaml")

    assert len(find_violations(tmp_path, tracked=None)) == 2


def test_fixtures_and_static_files_are_allowed(tmp_path: Path) -> None:
    _touch(tmp_path, "tests/fixtures/content/lessons/001/sources/demo.jpg")
    _touch(tmp_path, "tests/fixtures/content/lessons/001/lesson.yaml")
    _touch(tmp_path, "src/french_learning/web/static/img/logo.png")

    assert find_violations(tmp_path, tracked=None) == []


def test_only_tracked_files_are_checked_when_list_given(tmp_path: Path) -> None:
    _touch(tmp_path, "materials/photo.jpeg")

    assert find_violations(tmp_path, tracked=["pyproject.toml"]) == []
