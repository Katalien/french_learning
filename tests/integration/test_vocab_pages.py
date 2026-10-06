"""US2: словарь и карточка записи (FR-010–FR-014)."""

import re


def links(html: str) -> set[str]:
    return set(re.findall(r'href="/vocab/(voc-[a-z2-7]{8})(?:\?[^"]*)?"', html))


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
    # 0.9.1: род — в скобках сразу за словом: «la maison (f)»
    assert re.search(r'la maison\s*<span class="gender-label">\(f\)</span>', html)
    html = client.get("/vocab/voc-painaaaa").text
    assert "gender-m" in html and '<span class="gender-label">(m)</span>' in html


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


def word_links(html: str) -> list[str]:
    return re.findall(r'href="/vocab/(voc-[a-z]+)(?:\?[^"]*)?" class="dict-word"', html)


def test_list_links_keep_filters(client):
    """010 пункт 1: слово открывается с фильтрами списка — для переходов «‹ ›»."""
    html = client.get("/vocab?lesson=2").text
    assert re.search(r'href="/vocab/voc-[a-z]+\?lesson=2" class="dict-word"', html)
    assert re.search(r'href="/vocab/voc-[a-z]+" class="dict-word"', client.get("/vocab").text)


def test_entry_neighbours_follow_filtered_list(client):
    ids = word_links(client.get("/vocab?lesson=2").text)
    assert len(ids) == 2
    first = client.get(f"/vocab/{ids[0]}?lesson=2").text
    assert "1 из 2" in first
    assert 'class="card-arrow prev disabled"' in first
    assert f'href="/vocab/{ids[1]}?lesson=2"' in first and 'class="card-arrow next"' in first
    second = client.get(f"/vocab/{ids[1]}?lesson=2").text
    assert "2 из 2" in second
    assert f'href="/vocab/{ids[0]}?lesson=2"' in second
    assert 'class="card-arrow next disabled"' in second


def test_entry_without_filters_uses_whole_dictionary(client):
    ids = word_links(client.get("/vocab").text)
    html = client.get(f"/vocab/{ids[1]}").text
    assert f"2 из {len(ids)}" in html
    assert f'href="/vocab/{ids[0]}"' in html and f'href="/vocab/{ids[2]}"' in html


# --- 0.9.1: листание слов урока и темы, а не всего словаря ------------------------------------


def test_lesson_vocab_links_keep_lesson(client):
    html = client.get("/lessons/2/vocab").text
    ids = re.findall(r'href="/vocab/(voc-[a-z2-7]{8})\?from=lesson&amp;lesson=2"', html)
    assert len(ids) == 2  # все слова урока 2 — со ссылкой «из урока»
    first = client.get(f"/vocab/{ids[0]}?from=lesson&lesson=2").text
    assert "1 из 2" in first
    assert f'href="/vocab/{ids[1]}?from=lesson&amp;lesson=2"' in first
    assert 'href="/lessons/2/vocab"' in first  # путь назад — к лексике урока
    last = client.get(f"/vocab/{ids[1]}?from=lesson&lesson=2").text
    assert "2 из 2" in last and 'class="card-arrow next disabled"' in last


def test_topic_words_links_keep_topic(client):
    html = client.get("/topics/top-maisonxx?tab=words").text
    ids = re.findall(r'href="/vocab/(voc-[a-z2-7]{8})\?from=topic&amp;topic=top-maisonxx"', html)
    assert len(ids) == 2
    page = client.get(f"/vocab/{ids[0]}?from=topic&topic=top-maisonxx").text
    assert "1 из 2" in page
    assert f'href="/vocab/{ids[1]}?from=topic&amp;topic=top-maisonxx"' in page
    assert 'href="/topics/top-maisonxx' in page


def test_entry_card_layout(client):
    """0.9.1 (макет А): карточка по центру, стрелки по бокам карточки, «Подробнее» — под
    неизменной верхней частью (слово и переводы)."""
    html = client.get("/vocab/voc-maisonaa?topic=top-maisonxx").text
    row = html.split('class="word-card-row"', 1)[1]
    assert row.index('class="card-arrow prev') < row.index('class="word-card ')
    assert row.index('class="word-card ') < row.index('class="card-arrow next')
    card = row.split('class="word-card ', 1)[1].split("</article>", 1)[0]
    main = card.split('class="word-card-main"', 1)[1]
    assert main.index("дом") < main.index('class="entry-extra"')
    assert 'class="arrow ' not in html  # прежние стрелки у краёв окна убраны


def test_translation_origin_not_next_to_translation(client):
    """0.9.1: рядом с переводом метки происхождения нет; при включённом «Происхождении» она
    в «Подробнее» (конституция, принцип I — происхождение доступно в интерфейсе)."""
    client.cookies.set("show_origin", "1")
    html = client.get("/vocab/voc-maisonaa").text
    translations = html.split('class="translations"', 1)[1].split("</p>", 1)[0]
    assert "origin-badge" not in translations
    extra = html.split('class="entry-extra"', 1)[1].split("</details>", 1)[0]
    assert 'class="entry-origin' in extra and "origin-badge" in extra
    client.cookies.set("show_origin", "0")
    html = client.get("/vocab/voc-maisonaa").text
    assert "entry-origin" not in html


def test_entry_keyboard_arrows(client):
    """0.9.1: на компьютере ← / → листают слова (как стрелки у карточки)."""
    html = client.get("/vocab/voc-maisonaa?topic=top-maisonxx").text
    assert "data-keyboard-arrows" in html
    assert "ArrowLeft" in html and "ArrowRight" in html


# --- 011: фильтры «Лексики» урока -----------------------------------------------------------


def test_lesson_vocab_filters(client):
    html = client.get("/lessons/1/vocab").text
    topic_select = html.split('name="topic"', 1)[1].split("</select>", 1)[0]
    assert "Дом" in topic_select and "Еда" in topic_select and "Артикли" not in topic_select
    assert 'name="kind"' in html
    food = client.get("/lessons/1/vocab?topic=top-nourritu").text
    assert "pain" in food and "maison" not in food.split('class="word-rows"', 1)[1]
    assert re.search(r'<option value="top-nourritu"\s+selected', food)
    empty = client.get("/lessons/1/vocab?kind=verb").text
    assert "Нет слов для выбранных условий" in empty


def test_filtered_lesson_links_and_neighbours(client):
    html = client.get("/lessons/1/vocab?topic=top-nourritu").text
    link = 'href="/vocab/voc-painaaaa?from=lesson&amp;lesson=1&amp;topic=top-nourritu"'
    assert link in html
    page = client.get("/vocab/voc-painaaaa?from=lesson&lesson=1&topic=top-nourritu").text
    assert "1 из 1" in page
    assert 'class="card-arrow next disabled"' in page
    assert 'href="/lessons/1/vocab?topic=top-nourritu"' in page  # назад — с тем же фильтром
