"""Черновик и целостное сохранение (FR-032, FR-034, FR-035; research R3)."""

from pathlib import Path

import pytest
import yaml

from french_learning.agent import staging
from french_learning.content.loader import load_content
from tests.unit.agent.conftest import commits

NEW_EXERCISE = """\
id: ex-newexera
type: gap_input
kind: exercise
lesson: 4
part: class
number: 1
topics: [top-nasalson]
description_ru: Новое упражнение
instruction: {ru: Вставьте., original: Complétez., original_lang: fr, origin: ai}
origin: material
answers_origin: ai
sources:
  - {file: lessons/004/sources/sheet4.jpg, original: sheet4.jpg}
items:
  - {id: 1, text: "Le {{1}} est bon.", answers: {1: [pain]}}
"""


def stage(root: Path, relative: str, text: str, op: str = "op1") -> Path:
    path = root / ".staging" / op / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_stage_check_ok(store: Path):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE)
    result = staging.stage_check(store, "op1")
    assert result.ok and result.errors == []


def test_stage_check_reports_only_new_errors(store: Path):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE.replace("[pain]", "[]"))
    result = staging.stage_check(store, "op1")
    assert not result.ok
    assert [e.path for e in result.errors] == ["lessons/004/exercises/ex-newexera.yaml"]


def test_commit_with_errors_changes_nothing(store: Path):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", "id: [broken")
    result = staging.commit_staging(store, "op1", "Урок 4")
    assert not result.applied
    assert not (store / "lessons/004/exercises/ex-newexera.yaml").exists()
    assert (store / ".staging/op1").exists()
    assert commits(store) == ["init"]


def test_commit_applies_everything_in_one_commit(store: Path):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE)
    stage(store, "lessons/004/sources/new.jpg", "binary")
    (store / ".staging/op1/_delete.txt").write_text(
        "lessons/004/exercises/ex-reservea.yaml\n", encoding="utf-8"
    )
    result = staging.commit_staging(store, "op1", "Урок 4: 1 упражнение")
    assert result.applied and result.committed
    assert not result.pushed and "не отправлена" in result.warning
    content = load_content(store)
    assert "ex-newexera" in content.elements
    assert "ex-reservea" not in content.elements
    assert (store / "lessons/004/inventory.md").exists()
    assert (store / "index.md").exists()
    assert commits(store) == ["Урок 4: 1 упражнение", "init"]
    assert not (store / ".staging/op1").exists()


def test_failure_during_apply_rolls_back(store: Path, monkeypatch):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE)
    changed = NEW_EXERCISE.replace("ex-newexera", "ex-reservea").replace("number: 1", "number: 2")
    changed = changed.replace("part: class", "part: homework").replace("Новое", "Изменённое")
    stage(store, "lessons/004/exercises/ex-reservea.yaml", changed)
    original = (store / "lessons/004/exercises/ex-reservea.yaml").read_text(encoding="utf-8")

    calls = {"n": 0}
    real_replace = staging.os.replace

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("сбой диска")
        return real_replace(src, dst)

    monkeypatch.setattr(staging.os, "replace", flaky_replace)
    with pytest.raises(staging.StagingError):
        staging.commit_staging(store, "op1", "x")
    monkeypatch.undo()

    assert not (store / "lessons/004/exercises/ex-newexera.yaml").exists()
    assert (store / "lessons/004/exercises/ex-reservea.yaml").read_text(
        encoding="utf-8"
    ) == original
    assert commits(store) == ["init"]


def test_retry_after_fixing_draft(store: Path):
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE.replace("[pain]", "[]"))
    assert not staging.commit_staging(store, "op1", "x").applied
    stage(store, "lessons/004/exercises/ex-newexera.yaml", NEW_EXERCISE)
    assert staging.commit_staging(store, "op1", "Урок 4").applied


def test_reclassification_deletes_only_listed_elements(store: Path):
    """US3, FR-037: удаляются только элементы указанного файла, остальные id не меняются."""
    before = set(load_content(store).elements)
    (store / ".staging/op1").mkdir(parents=True)
    (store / ".staging/op1/_delete.txt").write_text(
        "lessons/001/exercises/ex-grouping.yaml\n", encoding="utf-8"
    )
    stage(
        store,
        "lessons/001/exercises/ex-newexera.yaml",
        NEW_EXERCISE.replace("lesson: 4", "lesson: 1")
        .replace("lessons/004/sources/sheet4.jpg", "lessons/001/sources/sheet.jpg")
        .replace("number: 1", "number: 5"),
    )
    assert staging.commit_staging(store, "op1", "Урок 1: переклассификация").applied
    after = set(load_content(store).elements)
    assert after == (before - {"ex-grouping"}) | {"ex-newexera"}


def test_delete_outside_storage_is_refused(store: Path):
    (store / ".staging/op1").mkdir(parents=True)
    (store / ".staging/op1/_delete.txt").write_text("../outside.txt\n", encoding="utf-8")
    with pytest.raises(staging.StagingError):
        staging.commit_staging(store, "op1", "x")


def test_journal_update_through_staging(store: Path):
    lesson = yaml.safe_load((store / "lessons/004/lesson.yaml").read_text(encoding="utf-8"))
    lesson["files"] = [
        {
            "path": "Leçon 04/sheet4.jpeg",
            "part": "homework",
            "sha256": "c" * 64,
            "classification": "exercises",
            "elements": ["ex-reservea"],
            "stored_as": "lessons/004/sources/sheet4.jpg",
        }
    ]
    stage(store, "lessons/004/lesson.yaml", yaml.safe_dump(lesson, allow_unicode=True))
    assert staging.commit_staging(store, "op1", "Журнал").applied
    assert load_content(store).lessons[4].files[0].elements == ["ex-reservea"]
