"""Запрос по индексу: группы, порядок, область и фильтры (007, research R4–R6).

Группы «Слова», «Темы», «Теория». Слова словаря не ищутся по одним артиклям.
Поиск ничего не сохраняет (FR-014).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from french_learning.search.index import Doc, SearchIndex
from french_learning.search.text import find, query_tokens, snippet

SCOPES = ("all", "words", "theory", "topics")
GROUPS = {"words": "word", "topics": "topic", "theory": "theory"}  # порядок показа
ARTICLES = {"le", "la", "les", "l", "un", "une", "des"}


@dataclass
class Query:
    q: str
    scope: str = "all"
    lesson: int | None = None
    topic: str | None = None

    def __post_init__(self) -> None:
        if self.scope not in SCOPES:
            self.scope = "all"
        self.topic = self.topic or None
        self.lesson = self.lesson or None


@dataclass
class Result:
    kind: str
    id: str
    title: str
    url: str
    translation: str | None = None
    lesson: int | None = None
    count: int = 0  # теория: совпадений в тексте
    snippet: list[tuple[str, bool]] | None = None
    rank: tuple = ()


@dataclass
class Results:
    query: Query
    groups: dict[str, list[Result]] = field(default_factory=dict)
    empty_reason: str | None = None  # short | none

    @property
    def total(self) -> int:
        return sum(len(items) for items in self.groups.values())


def _in_filters(doc: Doc, query: Query, index: SearchIndex) -> bool:
    if doc.kind == "topic":
        if query.topic and doc.id != query.topic:
            return False
        return not query.lesson or doc.id in index.lesson_topics.get(query.lesson, set())
    if query.topic and query.topic not in doc.topics:
        return False
    return not query.lesson or query.lesson in doc.lessons


def _match(doc: Doc, words: list[str], show_translation: bool) -> Result | None:
    hits = {f.name: find(f.tokens, words) for f in doc.fields}
    matched = [name for name, found in hits.items() if found]
    if not matched:
        return None
    result = Result(doc.kind, doc.id, doc.title, doc.url, lesson=doc.lesson_order or None)
    title = doc.title.casefold()
    if doc.kind == "word":
        result.translation = doc.translation if show_translation else None
        result.rank = (0 if "fr" in matched else 1, title)
    elif doc.kind == "theory":
        result.count = len(hits.get("text", []))
        if result.count:  # фрагмент вокруг первого совпадения в тексте (FR-012)
            text = next(f for f in doc.fields if f.name == "text")
            result.snippet = snippet(text.text, text.tokens, hits["text"][0], len(words))
        result.rank = (0 if "title" in matched else 1, -doc.lesson_order, title)
    else:
        result.rank = (title,)
    return result


def search(index: SearchIndex, query: Query, show_translation: bool = True) -> Results:
    results = Results(query, {group: [] for group in GROUPS})
    words = query_tokens(query.q)
    if not words:
        results.empty_reason = "short"
        return results
    only_articles = all(w in ARTICLES for w in words)
    wanted = {kind for group, kind in GROUPS.items() if query.scope in ("all", group)}
    for doc in index.docs:
        if doc.kind not in wanted or (doc.kind == "word" and only_articles):
            continue
        if not _in_filters(doc, query, index):
            continue
        result = _match(doc, words, show_translation)
        if result is not None:
            group = next(g for g, kind in GROUPS.items() if kind == doc.kind)
            results.groups[group].append(result)
    for items in results.groups.values():
        items.sort(key=lambda r: r.rank)
    if not results.total:
        results.empty_reason = "none"
    return results
