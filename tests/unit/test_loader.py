"""Загрузчик контента: чтение, проверка, изоляция ошибок (FR-005, правила 1–8)."""

from pathlib import Path

from french_learning.content.loader import load_content


def error_paths(content):
    return {e.path for e in content.errors}


def test_sample_loads_with_only_broken_file_failing(content_root: Path):
    content = load_content(content_root)

    assert error_paths(content) == {"lessons/002/exercises/ex-brokenaa.yaml"}
    assert sorted(content.lessons) == [1, 2, 4]
    assert "ex-brokenaa" not in content.elements
    assert content.errors[0].element_id == "ex-brokenaa"
    kinds = {e.kind for e in content.elements.values()}
    assert kinds == {"theory", "text", "exercise", "vocab"}
    assert "rep-openaaaa" in content.reports
    assert content.topics is not None


def test_clean_sample_has_no_errors(clean_content_root: Path):
    assert load_content(clean_content_root).errors == []


def test_markdown_body_is_loaded(clean_content_root: Path):
    theory = load_content(clean_content_root).elements["th-articles"]
    assert "| ед. ч. |" in theory.body
    assert theory.title.startswith("Определённые")


def test_invalid_yaml_is_isolated(clean_content_root: Path):
    (clean_content_root / "lessons/001/exercises/ex-gapinput.yaml").write_text(
        "id: [unclosed", encoding="utf-8"
    )
    content = load_content(clean_content_root)
    assert error_paths(content) == {"lessons/001/exercises/ex-gapinput.yaml"}
    assert "ex-gapchoic" in content.elements


def test_duplicate_ids(clean_content_root: Path):
    src = clean_content_root / "lessons/001/exercises/ex-gapinput.yaml"
    dup = src.read_text(encoding="utf-8").replace("number: 2", "number: 9")
    (clean_content_root / "lessons/001/exercises/copy.yaml").write_text(dup, encoding="utf-8")
    messages = " ".join(e.message for e in load_content(clean_content_root).errors)
    assert "ex-gapinput" in messages and "повтор" in messages


def test_unknown_topic_reference(clean_content_root: Path):
    path = clean_content_root / "lessons/001/exercises/ex-gapinput.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("top-etreverb", "top-unknownx"), encoding="utf-8"
    )
    content = load_content(clean_content_root)
    assert error_paths(content) == {"lessons/001/exercises/ex-gapinput.yaml"}
    assert "top-unknownx" in content.errors[0].message


def test_unknown_link_and_report_element(clean_content_root: Path):
    ex = clean_content_root / "lessons/001/exercises/ex-truefals.yaml"
    ex.write_text(
        ex.read_text(encoding="utf-8").replace("tx-aucafeaa", "tx-missingx"), encoding="utf-8"
    )
    rep = clean_content_root / "reports/rep-openaaaa.yaml"
    rep.write_text(
        rep.read_text(encoding="utf-8").replace("ex-gapchoic", "ex-missingx"), encoding="utf-8"
    )
    assert error_paths(load_content(clean_content_root)) == {
        "lessons/001/exercises/ex-truefals.yaml",
        "reports/rep-openaaaa.yaml",
    }


def test_missing_source_file_is_a_warning_and_element_stays(clean_content_root: Path):
    (clean_content_root / "lessons/001/sources/picture.jpg").unlink()
    content = load_content(clean_content_root)
    assert error_paths(content) == {"lessons/001/exercises/ex-picturea.yaml"}
    assert content.errors[0].warning is True
    assert "ex-picturea" in content.elements  # spec, Edge Cases: элемент показывается


def test_duplicate_exercise_number_in_same_part(clean_content_root: Path):
    path = clean_content_root / "lessons/001/exercises/ex-gapinput.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("number: 2", "number: 1"), encoding="utf-8"
    )
    messages = " ".join(e.message for e in load_content(clean_content_root).errors)
    assert "номер" in messages


def test_lesson_folder_must_match_number(clean_content_root: Path):
    (clean_content_root / "lessons/004").rename(clean_content_root / "lessons/005")
    content = load_content(clean_content_root)
    assert "lessons/005/lesson.yaml" in error_paths(content)


def test_unsupported_format_version(clean_content_root: Path):
    (clean_content_root / "format.yaml").write_text("format_version: 99\n", encoding="utf-8")
    content = load_content(clean_content_root)
    assert error_paths(content) == {"format.yaml"}
    assert content.elements == {}


def test_unknown_files_are_ignored(clean_content_root: Path):
    (clean_content_root / "inventory.md").write_text("# опись", encoding="utf-8")
    (clean_content_root / "lessons/001/notes.txt").write_text("x", encoding="utf-8")
    assert load_content(clean_content_root).errors == []


def test_journal_elements_must_exist(clean_content_root: Path):
    path = clean_content_root / "lessons/004/lesson.yaml"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "files:\n  - {path: a.jpg, part: homework, sha256: "
        + "b" * 64
        + ", classification: exercises, elements: [ex-missingx]}\n",
        encoding="utf-8",
    )
    content = load_content(clean_content_root)
    assert 4 in content.lessons  # урок остаётся, это предупреждение
    [error] = content.errors
    assert error.warning and "ex-missingx" in error.message


# --- 004: тренажёры ----------------------------------------------------------------------------


def test_trainers_and_batches_loaded(clean_content_root: Path):
    content = load_content(clean_content_root)
    assert [t.id for t in content.trainers] == ["negation", "articles"]
    batch = content.batches["tb-negaaaaa"]
    assert len(batch.items) == 5
    assert content.batch_paths["tb-negaaaaa"] == "trainers/negation/tb-negaaaaa.yaml"


def test_storage_without_trainers_is_valid(clean_content_root: Path):
    import shutil

    (clean_content_root / "trainers.yaml").unlink()
    shutil.rmtree(clean_content_root / "trainers")
    content = load_content(clean_content_root)
    assert content.errors == [] and content.trainers == [] and content.batches == {}


def test_batch_errors_are_isolated(clean_content_root: Path):
    folder = clean_content_root / "trainers"
    good = (folder / "negation" / "tb-negaaaaa.yaml").read_text(encoding="utf-8")
    (folder / "unknown").mkdir()
    (folder / "unknown" / "tb-unknownx.yaml").write_text(
        good.replace("tb-negaaaaa", "tb-unknownx").replace("trainer: negation", "trainer: unknown"),
        encoding="utf-8",
    )
    (folder / "negation" / "tb-wrongtyp.yaml").write_text(
        good.replace("tb-negaaaaa", "tb-wrongtyp").replace("type: transform", "type: gap_input"),
        encoding="utf-8",
    )
    content = load_content(clean_content_root)
    paths = {e.path for e in content.errors}
    assert paths == {"trainers/unknown/tb-unknownx.yaml", "trainers/negation/tb-wrongtyp.yaml"}
    assert set(content.batches) == {"tb-negaaaaa"}
