"""US2: «Открыть оригинал» — отдача исходников из хранилища (FR-034, research R9)."""

from pathlib import Path


def test_image_and_pdf_served_with_types(client):
    png = client.get("/sources/lessons/001/sources/scheme.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    pdf = client.get("/sources/lessons/001/sources/articles.pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"


def test_docx_shown_as_html(client):
    response = client.get("/sources/lessons/002/sources/etre.docx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "le verbe être" in response.text


def test_paths_outside_storage_are_refused(client):
    for path in ("/sources/..%2F..%2Fpyproject.toml", "/sources/%2E%2E/format.yaml"):
        assert client.get(path).status_code == 404


def test_only_source_files_are_served(client):
    # YAML-файлы контента не отдаются как «оригиналы»
    assert client.get("/sources/lessons/001/lesson.yaml").status_code == 404


def test_missing_source_shows_message_and_element_still_opens(client, content_root: Path):
    (content_root / "lessons/001/sources/picture.jpg").unlink()
    response = client.get("/sources/lessons/001/sources/picture.jpg")
    assert response.status_code == 404
    assert "Оригинал недоступен" in response.text
    assert client.get("/elements/ex-picturea").status_code == 200
    assert "Ошибка в данных" not in client.get("/elements/ex-picturea").text
