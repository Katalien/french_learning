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


def test_demo_init_creates_git_repo_without_broken_file(tmp_path: Path, capsys):
    target = tmp_path / "demo"
    assert cli.main(["demo-init", str(target)]) == 0
    assert (target / ".git").is_dir()
    assert (target / "lessons/001/lesson.yaml").exists()
    assert not (target / "lessons/002/exercises/ex-brokenaa.yaml").exists()
    assert cli.main(["validate-content", "--content-dir", str(target)]) == 0


def test_demo_init_with_broken_and_refuses_non_empty(tmp_path: Path):
    target = tmp_path / "demo"
    assert cli.main(["demo-init", str(target), "--with-broken"]) == 0
    assert (target / "lessons/002/exercises/ex-brokenaa.yaml").exists()
    assert cli.main(["demo-init", str(target)]) == 2


def test_not_found_page_is_russian_html(client):
    response = client.get("/lessons/99")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Урок 99 не найден" in response.text


def test_serve_binds_to_localhost_by_default(monkeypatch):
    calls = {}
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.setattr(cli, "_run_server", lambda app, host, port: calls.update(host=host))
    cli.main(["serve"])
    assert calls["host"] == "127.0.0.1"
