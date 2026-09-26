"""Команды: validate-content, serve (contracts/content-format.md, FR-053)."""

from pathlib import Path

from french_learning import cli


def test_validate_content_reports_broken_file(content_root: Path, capsys):
    code = cli.main(["validate-content", "--content-dir", str(content_root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "lessons/002/exercises/ex-brokenaa.yaml" in out


def test_validate_content_clean(clean_content_root: Path, capsys):
    code = cli.main(["validate-content", "--content-dir", str(clean_content_root)])
    assert code == 0
    assert "Нарушений нет" in capsys.readouterr().out


def test_serve_binds_to_localhost_by_default(monkeypatch):
    calls = {}
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setattr(cli, "_run_server", lambda app, host, port: calls.update(host=host))
    cli.main(["serve"])
    assert calls["host"] == "127.0.0.1"
