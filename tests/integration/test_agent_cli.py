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
