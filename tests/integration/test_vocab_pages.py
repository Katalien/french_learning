"""US2: словарь и карточка записи (FR-010–FR-014)."""

import re


def links(html: str) -> set[str]:
    return set(re.findall(r'href="/vocab/(voc-[a-z2-7]{8})"', html))


def test_dictionary_list_and_filters(client):
    assert links(client.get("/vocab").text) == {
        "voc-maisonaa",
        "voc-painaaaa",
        "voc-eauaaaaa",
        "voc-chataaaa",
    }
    assert links(client.get("/vocab?lesson=2").text) == {"voc-painaaaa", "voc-eauaaaaa"}
    assert links(client.get("/vocab?topic=top-maisonxx").text) == {"voc-maisonaa", "voc-chataaaa"}
    assert links(client.get("/vocab?kind=verb").text) == set()


def test_dictionary_rows(client):
    # 009: словарь строками — полоса рода, слово, перевод, урок, озвучка
    html = client.get("/vocab").text
    listing = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html))
    assert "la maison — дом" in listing
    assert 'class="gbar g-f"' in html and 'data-speak="la maison"' in html
    assert 'href="/practice' not in html.split("</header>", 1)[1]  # повторение — в «Практике»


def test_entry_page_gender_label_and_color(client):
    html = client.get("/vocab/voc-maisonaa").text
    assert "gender-f" in html
    assert '<span class="gender-label">f</span>' in html
    html = client.get("/vocab/voc-painaaaa").text
    assert "gender-m" in html and '<span class="gender-label">m</span>' in html


def test_entry_without_gender_is_neutral(client, content_root):
    path = content_root / "vocabulary/voc-chataaaa.yaml"
    text = path.read_text(encoding="utf-8").replace("gender: m\n", "").replace("article: le\n", "")
    path.write_text(text, encoding="utf-8")
    html = client.get("/vocab/voc-chataaaa").text
    assert "gender-none" in html and "gender-label" not in html


def test_extra_block_collapsed_with_details(client):
    html = client.get("/vocab/voc-painaaaa").text
    assert '<details class="entry-extra">' in html
    assert "Уроки" in html and "1, 2" in html


def test_speech_button(client):
    html = client.get("/vocab/voc-maisonaa").text
    assert 'data-speak="la maison"' in html
    assert "/static/js/speech.js" in html
    assert client.get("/static/js/speech.js").status_code == 200


def test_menu_links_to_dictionary(client):
    assert 'href="/vocab"' in client.get("/").text


def test_filters_apply_on_change_and_list_only_topics_with_words(client):
    html = client.get("/vocab").text
    assert html.count('onchange="this.form.requestSubmit()"') == 4
    assert 'value="top-maisonxx"' in html
    assert 'value="top-nasalson"' not in html


def test_entry_details_layout(client):
    # «Подробнее» (макеты 2026-09-30: В4 + Д1): урок и число повторений — одной строкой внизу,
    # без даты последнего повторения; пример — без «урок N» рядом
    import re

    html = client.get("/vocab/voc-painaaaa").text
    meta = re.search(r'class="entry-meta">(.*?)</p>', html, re.S)[1]
    assert "уроки 1, 2" in meta and "повторений ещё не было" in meta
    assert "последнее" not in html
    assert "<h3>Уроки</h3>" not in html and "<h3>Повторения</h3>" not in html
