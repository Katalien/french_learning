"""Попытки упражнений: черновик, первая проверка, отметки, «выполнено» (FR-006, FR-020–FR-022)."""

from pathlib import Path

import pytest

from french_learning.content.loader import load_content
from french_learning.exercises.attempts import AttemptStore, ExerciseProgress
from french_learning.practice.db import ProgressDB


@pytest.fixture
def env(clean_content_root: Path):
    db = ProgressDB(clean_content_root)
    elements = load_content(clean_content_root).elements
    yield AttemptStore(db), elements
    db.close()


def test_draft_is_saved_and_not_done(env):
    store, el = env
    store.save_draft(el["ex-gapchoic"], {"1": {"1": "le"}})
    attempt = store.current("ex-gapchoic")
    assert attempt.status == "draft" and attempt.answers == {"1": {"1": "le"}}
    assert not ExerciseProgress(store).is_done("ex-gapchoic")


def test_first_check_fixes_results_and_marks_done(env):
    store, el = env
    e = el["ex-gapchoic"]
    attempt = store.check(e, {"1": {"1": "le"}, "2": {"1": "la"}, "3": {"1": "les"}})
    assert attempt.status == "checked"
    assert attempt.first_status("1") == "correct" and attempt.first_status("2") == "wrong"
    assert attempt.current_status("2") == "wrong"
    assert ExerciseProgress(store).is_done("ex-gapchoic")  # независимо от результата


def test_fixed_self_after_highlight(env):
    store, el = env
    e = el["ex-gapchoic"]
    store.check(e, {"1": {"1": "la"}})
    attempt = store.check(e, {"1": {"1": "le"}})
    assert attempt.first_status("1") == "wrong"
    assert attempt.current_status("1") == "correct"
    assert attempt.marks == {"1": "fixed_self"}
    assert attempt.outcome("1") == "fixed_self"


def test_reveal_counts_as_error(env):
    store, el = env
    e = el["ex-gapchoic"]
    store.check(e, {"1": {"1": "la"}})
    store.reveal(e, 1)
    attempt = store.check(e, {"1": {"1": "le"}})
    assert attempt.marks["1"] == "revealed" and attempt.outcome("1") == "revealed"
    # «Показать ответ» у пункта, который ещё не проверялся, — тоже ошибка
    store.reveal(e, 3)
    assert store.current("ex-gapchoic").first_status("3") == "wrong"


def test_reveal_after_correct_first_is_not_error(env):
    store, el = env
    e = el["ex-gapchoic"]
    store.check(e, {"1": {"1": "le"}})
    assert store.reveal(e, 1).outcome("1") == "correct"


def test_spelling_choice_postpones_first_result(env):
    store, el = env
    e = el["ex-transfor"]
    pending = store.check(e, {"1": {"a": "je ne suis pas fatiguee"}})
    assert pending.current_status("1") == "choose" and pending.first_status("1") is None
    wrong = next(v for v in pending.variants("1", "a") if v != "Je ne suis pas fatiguée.")
    attempt = store.check(e, {"1": {"a": "je ne suis pas fatiguee", "a~choice": wrong}})
    assert attempt.first_status("1") == "wrong"


def test_open_answer_saved_without_check(env):
    store, el = env
    attempt = store.save_open(el["ex-openansw"], {"1": {"a": "Je mange du pain."}})
    assert attempt.status == "saved"
    assert ExerciseProgress(store).is_done("ex-openansw")


def test_restart_creates_new_empty_attempt(env):
    store, el = env
    e = el["ex-gapchoic"]
    first = store.check(e, {"1": {"1": "la"}})
    fresh = store.restart(e)
    assert fresh.id != first.id and fresh.answers == {} and fresh.status == "draft"
    assert [a.id for a in store.history("ex-gapchoic")] == [fresh.id, first.id]
    assert ExerciseProgress(store).is_done("ex-gapchoic")  # прошлая проверка засчитана
