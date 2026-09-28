"""009: правки при приёмке — добавление слов по шагам, вкладка по умолчанию, доп. материалы,
диапазоны чисел, оформление «Требует проверки» и сообщений."""

import re
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(content_root: Path):
    for args in (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
    ):
        subprocess.run(["git", "-C", str(content_root), *args], check=True, capture_output=True)


# --- 1. добавление слов: выбор способа и последовательное добавление --------------------------


def test_add_page_offers_two_modes(client):
    html = client.get("/vocab/add").text
    assert 'href="/vocab/add/one"' in html and 'href="/vocab/add/list"' in html
    assert 'action="/vocab/import"' in client.get("/vocab/add/list").text
    one = client.get("/vocab/add/one").text
    assert 'action="/vocab/add"' in one and 'name="sequence" value="1"' in one


@pytest.mark.usefixtures("git_repo")
def test_add_words_one_after_another(client):
    first = client.post(
        "/vocab/add",
        data={"quick": "le fromage - сыр", "topic": "top-nourritu", "lesson": "1", "sequence": "1"},
    )
    assert first.url.path == "/vocab/add/one"
    html = first.text
    assert "le fromage" in html and "Добавить следующее" in html
    assert re.search(r'<option value="top-nourritu" selected', html)  # тема сохранилась
    assert re.search(r'<option value="1" selected', html)  # урок сохранился
    second = client.post(
        "/vocab/add",
        data={
            "quick": "la pomme - яблоко",
            "topic": "top-nourritu",
            "sequence": "1",
            "added": re.search(r'name="added" value="([^"]*)"', html)[1],
        },
    ).text
    assert "le fromage" in second and "la pomme" in second  # список добавленных в этой серии
    assert 'href="/vocab?notice=' in second and "Завершить" in second


# --- 3. тема из раздела «Лексика» открывается на словах ----------------------------------------


def test_vocabulary_topic_opens_words_tab(client):
    html = client.get("/topics/top-maisonxx").text  # раздел vocabulary
    assert "tab: 'words'" in html
    grammar = client.get("/topics/top-articles").text
    assert "tab: 'words'" not in grammar


# --- 5. доп. материалы: материалы и лексика раздельно ------------------------------------------


def test_extras_split_materials_and_words(client):
    html = client.get("/extras").text
    materials = html.split('data-block="materials"', 1)[1].split("</section>", 1)[0]
    words = html.split('data-block="words"', 1)[1].split("</section>", 1)[0]
    assert "Артикли перед h" in materials and "chat" not in materials
    assert "chat" in words and "Артикли перед h" not in words


# --- 2. тренажёр «Числа»: диапазоны ------------------------------------------------------------


def start_numbers(client, **form):
    response = client.post("/trainers/numbers/start", data={"scope": "range", **form})
    return response.url.path.rsplit("/", 1)[-1]


def prompts(client, session, count):
    found = []
    for _ in range(count):
        html = client.get(f"/trainers/s/{session}").text
        match = re.search(r'class="trainer-prompt"[^>]*>\s*(\d+)\s*<', html)
        if not match:
            break
        found.append(int(match[1]))
        key = re.search(r'name="key" value="([^"]+)"', html)[1]
        client.post(f"/trainers/s/{session}/answer", data={"answer": "x", "key": key})
    return found


def test_numbers_setup_has_ranges(client):
    html = client.get("/trainers/numbers").text
    assert 'name="range"' in html and "70–99" in html
    assert 'name="range_from"' in html and 'name="range_to"' in html


def test_numbers_preset_range(client):
    numbers = prompts(client, start_numbers(client, range="70-99"), 10)
    assert numbers and all(70 <= n <= 99 for n in numbers)


def test_numbers_custom_range(client):
    session = start_numbers(client, range="custom", range_from="200", range_to="205")
    numbers = prompts(client, session, 10)
    assert sorted(numbers) == [200, 201, 202, 203, 204, 205]


# --- 4. «Требует проверки» и сообщения: строки не разъезжаются ---------------------------------


def test_review_rows(client):
    html = client.get("/review").text
    row = html.split('class="review-row', 1)[1].split("</li>", 1)[0]
    assert 'class="row-title"' in row and 'class="row-meta"' in row and 'class="row-note"' in row


def test_report_rows(client):
    html = client.get("/reports").text
    assert 'class="review-row' in html and "<table" not in html.split("</header>", 1)[1]


# --- вторая порция правок ---------------------------------------------------------------------


def test_one_line_hint_without_comma(client):
    html = client.get("/vocab/add/one").text
    assert 'placeholder="la pomme - яблоко"' in html and "la, pomme" not in html


@pytest.mark.usefixtures("git_repo")
def test_word_without_topic(client, content_root):
    html = client.get("/vocab/add/one").text
    assert '<option value="">без темы</option>' in html
    response = client.post("/vocab/add", data={"quick": "le beurre - масло", "topic": ""})
    assert "/vocab/voc-" in str(response.url)
    [path] = [
        p for p in (content_root / "vocabulary").glob("*.yaml") if "beurre" in p.read_text("utf-8")
    ]
    assert "topics: []" in path.read_text("utf-8")
    listed = client.post("/vocab/import", data={"text": "le sel — соль", "topic": ""}).text
    assert "Добавлено: 1" in listed


def test_element_rows_title_first(client):
    html = client.get("/topics/top-articles?tab=exercises").text
    row = html.split('class="element-row', 1)[1].split("</li>", 1)[0]
    assert row.index('class="row-title"') < row.index('class="row-meta"')


def test_extras_words_behind_tab(client):
    html = client.get("/extras").text
    assert "tab: 'materials'" in html
    assert re.search(r"Лексика без урока<span class=\"count\">1</span>", html)
    assert "tab: 'words'" in client.get("/extras?tab=words").text
