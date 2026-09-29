"""Поисковый индекс по контенту (007, research R1, R4, R6; data-model «Документ индекса»).

Строится в памяти для текущего `ContentIndex` и кешируется по нему: `ContentStore`
пересоздаёт `ContentIndex` при изменении файлов, поэтому поиск видит правки без перезапуска.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from french_learning.content.index import ContentIndex
from french_learning.content.render import render_markdown
from french_learning.search.text import Token, tokens
from french_learning.vocab.entries import display_fr

_BLOCKS = {"p", "li", "td", "th", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br", "div", "table"}


@dataclass
class Field:
    name: str
    text: str
    tokens: list[Token]


def _field(name: str, text: str) -> Field:
    return Field(name, text, tokens(text))


@dataclass
class Doc:
    kind: str  # word | topic | theory
    id: str
    title: str
    url: str
    fields: list[Field]
    translation: str | None = None
    lessons: set[int] = field(default_factory=set)
    topics: set[str] = field(default_factory=set)
    lesson_order: int = 0


@dataclass
class SearchIndex:
    docs: list[Doc]
    lesson_topics: dict[int, set[str]]


class _Text(HTMLParser):
    """Текст отрендеренного markdown — то, что видит пользователь, без разметки."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in _BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(markdown: str) -> str:
    parser = _Text()
    parser.feed(render_markdown(markdown, ""))
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def _word(entry: Any) -> Doc:
    lessons = set(entry.lessons)
    lessons |= {t.lesson for t in entry.translations if t.lesson}
    lessons |= {x.lesson for x in entry.examples if x.lesson}
    title = display_fr(entry)
    translations = [t.text for t in entry.translations]
    return Doc(
        "word",
        entry.id,
        title,
        f"/vocab/{entry.id}",
        [_field("fr", title), *(_field("ru", t) for t in translations)],
        translation=", ".join(translations),
        lessons=lessons,
        topics=set(entry.topics),
    )


def _theory(element: Any) -> Doc:
    return Doc(
        "theory",
        element.id,
        element.title,
        f"/elements/{element.id}",
        [_field("title", element.title), _field("text", plain_text(element.body))],
        lessons={element.lesson} if element.lesson else set(),
        topics=set(element.topics),
        lesson_order=element.lesson or 0,
    )


def build(index: ContentIndex) -> SearchIndex:
    docs: list[Doc] = []
    lesson_topics: dict[int, set[str]] = {}
    for element in index.content.elements.values():
        if element.kind == "vocab":
            if element.hidden:
                continue
            doc = _word(element)
            docs.append(doc)
            for lesson in doc.lessons:
                lesson_topics.setdefault(lesson, set()).update(doc.topics)
        else:
            if element.lesson:
                lesson_topics.setdefault(element.lesson, set()).update(element.topics)
            if element.kind == "theory":
                docs.append(_theory(element))
    for topic in index.all_topics():
        docs.append(
            Doc("topic", topic.id, topic.name, f"/topics/{topic.id}", [_field("title", topic.name)])
        )
    return SearchIndex(docs, lesson_topics)


_cache: weakref.WeakKeyDictionary[ContentIndex, SearchIndex] = weakref.WeakKeyDictionary()


def search_index(index: ContentIndex) -> SearchIndex:
    """Индекс текущей версии контента (research R1)."""
    found = _cache.get(index)
    if found is None:
        found = _cache[index] = build(index)
    return found
