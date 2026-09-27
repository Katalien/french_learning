"""Команды для навыков: регистрация, JSON в stdout, коды выхода (contracts/cli.md)."""

import json
from pathlib import Path

import pytest

from french_learning import cli
from tests.unit.agent.conftest import store  # noqa: F401  (фикстура)

COMMANDS = [
    "init-content",
    "new-ids",
    "stage-check",
    "commit-staging",
    "build-archive",
    "scan-lesson",
    "store-source",
    "next-number",
    "topics-list",
    "vocab-find",
    "reports-list",
    "report-resolve",
    "quality-sample",
    "trainers-list",
    "trainer-context",
    "mistakes-list",
]


def run(capsys, *args: str) -> tuple[int, str, str]:
    code = cli.main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.parametrize("command", COMMANDS)
def test_command_registered(command, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main([command, "--help"])
    assert exc.value.code == 0


def test_new_ids_json(store: Path, capsys):  # noqa: F811
    code, out, _ = run(capsys, "new-ids", "ex", "--count", "3", "--content-dir", str(store))
    assert code == 0
    assert len(json.loads(out)) == 3


def test_stage_check_json_and_exit_codes(store: Path, capsys):  # noqa: F811
    code, out, _ = run(capsys, "stage-check", "--op", "op1", "--content-dir", str(store))
    assert code == 0 and json.loads(out)["ok"] is True

    bad = store / ".staging/op1/lessons/001/exercises/ex-badbadaa.yaml"
    bad.parent.mkdir(parents=True)
    bad.write_text("id: [broken", encoding="utf-8")
    code, out, _ = run(capsys, "stage-check", "--op", "op1", "--content-dir", str(store))
    assert code == 1
    assert json.loads(out)["errors"][0]["path"].endswith("ex-badbadaa.yaml")


def test_writing_command_refuses_storage_without_git(clean_content_root: Path, capsys):
    code, _, err = run(
        capsys, "commit-staging", "--op", "x", "-m", "x", "--content-dir", str(clean_content_root)
    )
    assert code == 2
    assert "git" in err


def test_init_content_and_build_archive(tmp_path: Path, capsys):
    root = tmp_path / "materials"
    assert run(capsys, "init-content", str(root))[0] == 0
    assert run(capsys, "build-archive", "--content-dir", str(root))[0] == 0
    assert (root / "index.md").exists()


# --- 004: тренажёры ----------------------------------------------------------------------------


def test_trainers_list(store: Path, capsys):  # noqa: F811
    code, out, _ = run(capsys, "trainers-list", "--content-dir", str(store))
    trainers = {t["id"]: t for t in json.loads(out)}
    assert code == 0 and "articles" in trainers
    assert trainers["negation"]["source"] == "agent" and trainers["negation"]["in_pool"] == 5
    assert trainers["negation"]["exercise_type"] == "transform"


def test_trainer_context(store: Path, capsys):  # noqa: F811
    code, out, _ = run(capsys, "trainer-context", "negation", "--content-dir", str(store))
    data = json.loads(out)
    assert code == 0
    assert "ne … pas" in data["trainer"]["rules"]
    assert any(v["text"] == "maison" for v in data["vocabulary"])
    assert data["lessons"][0]["topics"]
    assert "Je suis fatiguée." in data["existing_tasks"]
    assert data["limits"]["max_new_words_per_item"] == 2
    code, _, err = run(capsys, "trainer-context", "unknown", "--content-dir", str(store))
    assert code == 2 and "/add-trainer" in err


def test_mistakes_list(store: Path, capsys):  # noqa: F811
    from french_learning.content.loader import load_content
    from french_learning.exercises.attempts import AttemptStore
    from french_learning.practice.db import ProgressDB
    from french_learning.trainers.schedule import TrainerSchedule

    db = ProgressDB(store)
    exercise = load_content(store).elements["ex-gapinput"]
    AttemptStore(db).check(exercise, {"1": {"1": "es"}, "2": {"1": "sommes"}})
    TrainerSchedule(db).answer(
        "negation", "tb-negaaaaa:2", correct=False, answer="Il mange pas de pain.", srs=False
    )
    db.close()
    code, out, _ = run(capsys, "mistakes-list", "--lesson", "1", "--content-dir", str(store))
    [item] = json.loads(out)["lessons"]
    assert code == 0 and item["exercise"] == "ex-gapinput" and item["answer"] == ["es"]
    assert item["correct"] == ["suis"]
    code, out, _ = run(
        capsys, "mistakes-list", "--trainer", "negation", "--content-dir", str(store)
    )
    [task] = json.loads(out)["trainer"]
    assert task["answers"] == ["Il mange pas de pain."]
    assert task["correct"] == ["Il ne mange pas de pain."]


def test_batch_through_staging(store: Path, capsys):  # noqa: F811
    target = store / ".staging/op1/trainers/negation/tb-newbatch.yaml"
    target.parent.mkdir(parents=True)
    source = (store / "trainers/negation/tb-negaaaaa.yaml").read_text(encoding="utf-8")
    target.write_text(source.replace("tb-negaaaaa", "tb-newbatch"), encoding="utf-8")
    code, out, _ = run(capsys, "stage-check", "--op", "op1", "--content-dir", str(store))
    assert code == 0, out
    assert run(capsys, "new-ids", "tb", "--content-dir", str(store))[0] == 0
