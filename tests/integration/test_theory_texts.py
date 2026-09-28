"""US2: теория, лексика, тексты и связи с упражнениями (FR-027, FR-033, FR-037, FR-039)."""


def test_theory_page_renders_table_image_and_toc(client):
    html = client.get("/lessons/1/theory").text
    assert "<table>" in html
    assert 'src="/sources/lessons/001/sources/scheme.png"' in html
    # 3 заголовка → оглавление со ссылками на них
    assert 'class="toc"' in html
    assert 'href="#th-articles-1"' in html and 'id="th-articles-1"' in html
    assert "Элизия" in html


def test_theory_page_links_to_related_exercises(client):
    html = client.get("/lessons/1/theory").text
    assert 'href="/elements/ex-gapchoic"' in html


def test_vocabulary_new_and_repeat(client):
    html = client.get("/lessons/1/vocab").text  # 009: лексика — отдельный раздел
    assert "la maison" in html and "дом" in html
    assert "На повторение" not in html

    html = client.get("/lessons/2/vocab").text
    new_part, repeat_part = html.split("На повторение")
    assert "l'eau" in new_part.replace("&#39;", "'")
    assert "le pain" in repeat_part


def test_texts_page_is_separate_from_theory(client):
    html = client.get("/lessons/1/texts").text
    assert "Au café (démo)" in html
    assert 'href="/elements/ex-truefals"' in html
    assert 'href="/elements/ex-choicecf"' in html
    assert "Au café (démo)" not in client.get("/lessons/1/theory").text


def test_exercise_links_back_to_text_and_theory(client):
    assert 'href="/elements/tx-aucafeaa"' in client.get("/elements/ex-truefals").text
    assert 'href="/elements/th-articles"' in client.get("/elements/ex-gapchoic").text


def test_theory_element_page_lists_exercises(client):
    html = client.get("/elements/th-articles").text
    assert 'href="/elements/ex-gapchoic"' in html
