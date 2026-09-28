"""Схема формата контента (contracts/content-format.md, data-model.md)."""

import pytest
from pydantic import TypeAdapter, ValidationError

from french_learning.content import schema

EXERCISE = TypeAdapter(schema.Exercise)


def exercise(**overrides):
    data = {
        "id": "ex-abcdefgh",
        "kind": "exercise",
        "type": "gap_input",
        "lesson": 1,
        "part": "homework",
        "number": 1,
        "topics": ["top-abcdefgh"],
        "description_ru": "Описание",
        "instruction": {"ru": "Сделайте.", "original": "Faites.", "original_lang": "fr"},
        "origin": "material",
        "sources": [{"file": "lessons/001/sources/a.jpg"}],
        "items": [{"id": 1, "text": "Je {{1}} ici.", "answers": {1: ["suis"]}}],
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "value", ["ex-abcdefgh", "top-23456722", "les-zzzzzzzz", "rep-a2b3c4d5", "voc-aaaaaaaa"]
)
def test_valid_ids(value):
    assert TypeAdapter(schema.Id).validate_python(value) == value


@pytest.mark.parametrize(
    "value", ["ex-abc", "xx-abcdefgh", "ex-ABCDEFGH", "ex-abcdefg1", "ex-abcdefgh9", "exabcdefgh"]
)
def test_invalid_ids(value):
    with pytest.raises(ValidationError):
        TypeAdapter(schema.Id).validate_python(value)


def test_part_origin_status_values():
    EXERCISE.validate_python(exercise(part="class", status="optional", origin="ai"))
    for field, bad in [("part", "lab"), ("status", "hidden"), ("origin", "teacher")]:
        with pytest.raises(ValidationError):
            EXERCISE.validate_python(exercise(**{field: bad}))


def test_needs_review_requires_note():
    with pytest.raises(ValidationError, match="note"):
        schema.NeedsReview(flag=True)
    assert schema.NeedsReview(flag=True, note="плохо читается").flag


def test_part_required_when_lesson_given():
    with pytest.raises(ValidationError, match="part"):
        EXERCISE.validate_python(exercise(part=None))


def test_element_without_lesson_needs_no_part():
    ex = EXERCISE.validate_python(exercise(lesson=None, part=None))
    assert ex.lesson is None


def test_topics_required_unless_needs_review():
    with pytest.raises(ValidationError, match="topic"):
        EXERCISE.validate_python(exercise(topics=[]))
    EXERCISE.validate_python(
        exercise(topics=[], needs_review={"flag": True, "note": "тема не определена"})
    )


def test_sources_required_unless_user_origin():
    with pytest.raises(ValidationError, match="sources"):
        EXERCISE.validate_python(exercise(sources=[]))
    EXERCISE.validate_python(exercise(sources=[], origin="user"))


def test_source_ref_needs_file_or_url():
    with pytest.raises(ValidationError):
        schema.SourceRef()
    assert schema.SourceRef(url="https://example.com").url


def test_gap_count_must_match_answers():
    bad = [{"id": 1, "text": "Je {{1}} {{2}}.", "answers": {1: ["suis"]}}]
    with pytest.raises(ValidationError, match="пропуск"):
        EXERCISE.validate_python(exercise(items=bad))


def test_gap_answers_must_not_be_empty():
    bad = [{"id": 1, "text": "Je {{1}}.", "answers": {1: []}}]
    with pytest.raises(ValidationError):
        EXERCISE.validate_python(exercise(items=bad))


def test_gap_choice_answers_must_be_options_case_insensitive():
    items = [{"id": 1, "text": "{{1}} chat.", "answers": {1: ["Le"]}}]
    EXERCISE.validate_python(exercise(type="gap_choice", options=["le", "la"], items=items))
    bad = [{"id": 1, "text": "{{1}} chat.", "answers": {1: ["les"]}}]
    with pytest.raises(ValidationError, match="вариант"):
        EXERCISE.validate_python(exercise(type="gap_choice", options=["le", "la"], items=bad))


def test_multi_gap_needs_two_gaps():
    one_gap = [{"id": 1, "text": "Je {{1}}.", "answers": {1: ["suis"]}}]
    with pytest.raises(ValidationError, match="2"):
        EXERCISE.validate_python(exercise(type="multi_gap", items=one_gap))


def test_choice_answer_indices_in_range():
    item = {"id": 1, "question": "?", "options": ["a", "b"], "answer": [2]}
    with pytest.raises(ValidationError, match="индекс"):
        EXERCISE.validate_python(exercise(type="choice", items=[item]))


def test_two_forms_answer_is_one_of_forms():
    item = {"id": 1, "text": "{{1}}", "forms": ["le", "les"], "answers": {1: ["la"]}}
    with pytest.raises(ValidationError):
        EXERCISE.validate_python(exercise(type="two_forms", items=[item]))


def test_grouping_answer_is_a_group():
    items = [{"id": 1, "word": "chat", "answer": "neutre"}]
    with pytest.raises(ValidationError, match="групп"):
        EXERCISE.validate_python(exercise(type="grouping", groups=["m", "f"], items=items))


def test_picture_requires_show_source():
    items = [{"id": 1, "prompt": "un stylo", "answers": []}]
    with pytest.raises(ValidationError, match="show_source"):
        EXERCISE.validate_python(exercise(type="picture", items=items))
    EXERCISE.validate_python(exercise(type="picture", show_source=True, items=items))


def test_open_has_no_answers():
    items = [{"id": 1, "prompt": "Racontez", "answers": ["x"]}]
    with pytest.raises(ValidationError):
        EXERCISE.validate_python(exercise(type="open", items=items))


def test_number_at_least_one():
    with pytest.raises(ValidationError):
        EXERCISE.validate_python(exercise(number=0))


def test_topics_file_unique_names_and_known_sections():
    ok = {
        "sections": [{"id": "grammar", "name": "Грамматика"}],
        "topics": [{"id": "top-abcdefgh", "name": "Артикли", "section": "grammar"}],
    }
    schema.TopicsFile.model_validate(ok)
    dup = dict(ok, topics=ok["topics"] + [dict(ok["topics"][0], id="top-bbbbbbbb", name="артикли")])
    with pytest.raises(ValidationError, match="имя"):
        schema.TopicsFile.model_validate(dup)
    unknown = dict(ok, topics=[dict(ok["topics"][0], section="nope")])
    with pytest.raises(ValidationError, match="раздел"):
        schema.TopicsFile.model_validate(unknown)


def test_vocab_entry_has_no_lesson_or_part():
    entry = {
        "id": "voc-abcdefgh",
        "kind": "vocab",
        "entry_type": "word",
        "text": "maison",
        "article": "la",
        "gender": "f",
        "translations": [{"text": "дом", "origin": "material"}],
        "lessons": [1],
        "topics": ["top-abcdefgh"],
        "origin": "user",
    }
    assert schema.VocabEntry.model_validate(entry).lessons == [1]
    with pytest.raises(ValidationError):
        schema.VocabEntry.model_validate(dict(entry, translations=[]))


# --- Дополнения функции 002: журнал файлов урока и закрытие сообщений ---------------------

SHA = "a" * 64


def lesson(**overrides):
    data = {"id": "les-abcdefgh", "number": 7, "source_folder": "Leçon 07"}
    data.update(overrides)
    return data


def test_lesson_without_files_is_valid():
    assert schema.Lesson.model_validate(lesson()).files == []


def test_lesson_file_entries():
    files = [
        {
            "path": "Leçon 07/IMG_1.jpeg",
            "part": "class",
            "sha256": SHA,
            "classification": "exercises",
            "elements": ["ex-abcdefgh"],
            "stored_as": "lessons/007/sources/img-1.jpg",
        },
        {
            "path": "Leçon 07/dup.jpeg",
            "part": "class",
            "sha256": SHA,
            "classification": "duplicate",
            "elements": [],
            "note": "дубль Devoirs/IMG_0101.jpeg",
        },
    ]
    assert len(schema.Lesson.model_validate(lesson(files=files)).files) == 2


@pytest.mark.parametrize("classification", ["duplicate", "unrecognized", "skipped"])
def test_note_required_for_non_processed_files(classification):
    entry = {"path": "a.jpg", "part": "class", "sha256": SHA, "classification": classification}
    with pytest.raises(ValidationError, match="note"):
        schema.Lesson.model_validate(lesson(files=[entry]))


def test_file_classification_and_hash_are_checked():
    bad_class = {"path": "a", "part": "class", "sha256": SHA, "classification": "photo"}
    bad_hash = {"path": "a", "part": "class", "sha256": "xyz", "classification": "theory"}
    for entry in (bad_class, bad_hash):
        with pytest.raises(ValidationError):
            schema.Lesson.model_validate(lesson(files=[entry]))


def test_file_paths_unique_in_lesson():
    entry = {"path": "a.jpg", "part": "class", "sha256": SHA, "classification": "theory"}
    with pytest.raises(ValidationError, match="повторяется"):
        schema.Lesson.model_validate(lesson(files=[entry, entry]))


def test_report_resolved_optional():
    report = {
        "id": "rep-abcdefgh",
        "element": "ex-abcdefgh",
        "comment": "x",
        "created": "2026-09-27T10:00:00",
        "status": "fixed",
        "resolution": "исправлено",
        "resolved": "2026-09-28T09:00:00",
    }
    assert schema.Report.model_validate(report).resolved is not None


def test_vocab_hidden_and_completed_by_ai():
    entry = {
        "id": "voc-abcdefgh",
        "kind": "vocab",
        "entry_type": "word",
        "text": "chat",
        "translations": [{"text": "кот", "origin": "user"}],
        "topics": ["top-abcdefgh"],
        "origin": "user",
    }
    plain = schema.VocabEntry.model_validate(entry)
    assert plain.hidden is False and plain.completed_by_ai == []
    extended = schema.VocabEntry.model_validate(
        dict(entry, hidden=True, completed_by_ai=["gender", "article"])
    )
    assert extended.hidden and extended.completed_by_ai == ["gender", "article"]


# --- 004: каталог тренажёров и пакеты заданий ------------------------------------------------


def batch(**overrides):
    data = {
        "id": "tb-abcdefgh",
        "kind": "task_batch",
        "trainer": "negation",
        "type": "transform",
        "created": "2026-09-27T18:00:00",
        "origin": "ai",
        "instruction_ru": "Сделайте отрицательным.",
        "items": [{"id": 1, "prompt": "Je suis là.", "answers": ["Je ne suis pas là."]}],
    }
    data.update(overrides)
    return schema.TaskBatch.model_validate(data)


def test_task_batch_valid_and_new_words_limit():
    assert batch().items[0].answers == ["Je ne suis pas là."]
    words = [{"text": f"w{i}", "translation": "т"} for i in range(3)]
    item = {"id": 1, "prompt": "p", "answers": ["a"], "new_words": words}
    with pytest.raises(ValidationError):
        batch(items=[item])
    assert batch(items=[{**item, "new_words": words[:2]}]).items[0].new_words[1].text == "w1"


def test_task_batch_items_follow_exercise_rules():
    gap = {"id": 1, "text": "Je {{1}} là.", "answers": {1: ["suis"]}}
    assert batch(type="gap_input", items=[gap]).items[0].gaps == [1]
    with pytest.raises(ValidationError):  # ответа нет среди вариантов
        batch(type="gap_choice", options=["es", "est"], items=[gap])
    with pytest.raises(ValidationError):  # тип не поддерживается пакетами
        batch(type="grouping", items=[{"id": 1, "word": "chat", "answer": "m"}])
    with pytest.raises(ValidationError):
        batch(id="ex-abcdefgh")


def test_trainer_entries():
    own = schema.TrainerEntry.model_validate(
        {"id": "negation", "name": "Отрицание", "description": "d", "exercise_type": "transform"}
    )
    assert own.source == "agent"
    override = schema.TrainerEntry.model_validate({"id": "articles", "source": "agent"})
    assert override.builtin
    with pytest.raises(ValidationError):  # у встроенного нельзя менять название
        schema.TrainerEntry.model_validate({"id": "articles", "name": "x"})
    with pytest.raises(ValidationError):  # у своего нужны название и тип
        schema.TrainerEntry.model_validate({"id": "negation", "name": "x"})
    with pytest.raises(ValidationError):
        schema.TrainerEntry.model_validate(
            {"id": "Bad id", "name": "x", "description": "d", "exercise_type": "transform"}
        )
    with pytest.raises(ValidationError):  # своему нельзя быть встроенным
        schema.TrainerEntry.model_validate(
            {
                "id": "mine",
                "name": "x",
                "description": "d",
                "exercise_type": "transform",
                "source": "builtin",
            }
        )


def test_report_may_point_to_batch():
    report = schema.Report.model_validate(
        {
            "id": "rep-abcdefgh",
            "element": "tb-abcdefgh",
            "item": 2,
            "comment": "c",
            "created": "2026-09-27T18:00:00",
        }
    )
    assert report.element == "tb-abcdefgh"


def test_vocab_may_have_no_topic():
    # 009: у слова темы может не быть (у остальных элементов тема или «требует проверки» нужны)
    entry = schema.VocabEntry.model_validate(
        {
            "id": "voc-abcdefgh",
            "kind": "vocab",
            "entry_type": "word",
            "text": "chat",
            "translations": [{"text": "кот", "origin": "user"}],
            "origin": "user",
        }
    )
    assert entry.topics == []
