"""Поисковый индекс по контенту (007, research R1, R4, R6; data-model «Документ индекса»)."""

from pathlib import Path

import pytest

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.search.index import build, search_index
from french_learning.search.text import find


@pytest.fixture
def content(clean_content_root: Path) -> ContentIndex:
    return ContentIndex(load_content(clean_content_root))


def docs(index, kind):
    return {d.id: d for d in build(index).docs if d.kind == kind}


def field(doc, name):
    return [f for f in doc.fields if f.name == name]


def test_words_have_french_with_article_and_translations(content):
    words = docs(content, "word")
    maison = words["voc-maisonaa"]
    assert maison.title == "la maison" and maison.url == "/vocab/voc-maisonaa"
    assert [f.text for f in field(maison, "fr")] == ["la maison"]
    assert [f.text for f in field(maison, "ru")] == ["дом"]
    assert maison.translation == "дом"
    assert words["voc-eauaaaaa"].title == "l'eau"
    assert find(field(words["voc-eauaaaaa"], "fr")[0].tokens, ["eau"]) == [1]


def test_word_lessons_include_translation_and_example_lessons(content):
    words = docs(content, "word")
    assert words["voc-painaaaa"].lessons == {1, 2}
    assert words["voc-chataaaa"].lessons == set()
    assert words["voc-maisonaa"].topics == {"top-maisonxx"}


def test_word_lessons_from_text_added_words(clean_content_root: Path):
    # слово, добавленное из текста (006): урок только у перевода и примера
    (clean_content_root / "vocabulary" / "voc-acheterx.yaml").write_text(
        "id: voc-acheterx\nkind: vocab\nentry_type: verb\ntext: acheter\n"
        "translations:\n  - {text: покупать, lesson: 2, origin: service}\n"
        "examples:\n  - {text: Elles achètent des pommes., lesson: 3}\n"
        "topics: []\norigin: user\n",
        encoding="utf-8",
    )
    index = ContentIndex(load_content(clean_content_root))
    assert docs(index, "word")["voc-acheterx"].lessons == {2, 3}


def test_hidden_words_are_not_indexed(clean_content_root: Path):
    path = clean_content_root / "vocabulary" / "voc-chataaaa.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "hidden: true\n", encoding="utf-8")
    index = ContentIndex(load_content(clean_content_root))
    assert "voc-chataaaa" not in docs(index, "word")


def test_theory_title_and_rendered_text_without_markup(content):
    theory = docs(content, "theory")
    articles = theory["th-articles"]
    assert articles.url == "/elements/th-articles" and articles.lessons == {1}
    assert articles.title == "Определённые артикли (демо)"
    text = field(articles, "text")[0].text
    for visible in ("Формы", "Мужской род", "ami", "Le chat dort", "Кот спит"):
        assert visible in text
    for markup in ("|", "##", "---", "scheme.png"):
        assert markup not in text


def test_theory_of_extras_without_lesson(content):
    extra = docs(content, "theory")["th-extrarul"]
    assert extra.lessons == set() and extra.lesson_order == 0


def test_topics_by_name_and_lesson_topics(content):
    topics = docs(content, "topic")
    assert topics["top-maisonxx"].title == "Дом"
    assert topics["top-maisonxx"].url == "/topics/top-maisonxx"
    index = build(content)
    assert "top-articles" in index.lesson_topics[1]  # тема теории урока 1
    assert "top-maisonxx" in index.lesson_topics[1]  # тема слова урока 1


def test_index_cached_per_content_version(clean_content_root: Path, content):
    assert search_index(content) is search_index(content)
    fresh = ContentIndex(load_content(clean_content_root))
    assert search_index(fresh) is not search_index(content)
