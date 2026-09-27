"""Формат контента, версия 1 — договор между агентом и приложением.

Описание: specs/001-lesson-content-view/contracts/content-format.md и data-model.md.
Схема используется и приложением при загрузке, и командой `validate-content` (агент, 002).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

FORMAT_VERSION = 1

_ID_TAIL = r"[a-z2-7]{8}"


def _id(prefix: str) -> type[str]:
    return Annotated[str, StringConstraints(pattern=rf"^{prefix}-{_ID_TAIL}$")]


Id = Annotated[str, StringConstraints(pattern=rf"^(les|th|tx|ex|voc|top|rep)-{_ID_TAIL}$")]
LessonId = _id("les")
TheoryId = _id("th")
TextId = _id("tx")
ExerciseId = _id("ex")
VocabId = _id("voc")
TopicId = _id("top")
ReportId = _id("rep")

Part = Literal["class", "homework"]
Origin = Literal["material", "external", "user", "ai", "service"]
Status = Literal["main", "optional", "reserve"]

GAP_RE = re.compile(r"\{\{(\d+)\}\}")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NeedsReview(Model):
    flag: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def _note_required(self) -> NeedsReview:
        if self.flag and not self.note:
            raise ValueError("при flag: true обязательно пояснение note")
        return self


class SourceRef(Model):
    file: str | None = None
    original: str | None = None
    page: int | None = None
    url: str | None = None

    @model_validator(mode="after")
    def _file_or_url(self) -> SourceRef:
        if bool(self.file) == bool(self.url):
            raise ValueError("укажите ровно одно из полей: file или url")
        return self


# --- Урок, темы, сообщения -------------------------------------------------------------------


class Media(Model):
    name: str
    type: Literal["audio", "video"]
    part: Part
    path: str


FileClassification = Literal[
    "theory",
    "vocabulary",
    "text",
    "exercises",
    "exercises_with_reference",
    "media",
    "duplicate",
    "unrecognized",
    "skipped",
]


class LessonFile(Model):
    """Запись журнала обработанных файлов урока (функция 002, data-model)."""

    path: str
    part: Part
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    classification: FileClassification
    elements: list[Id] = []
    stored_as: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _note_when_not_processed(self) -> LessonFile:
        if self.classification in {"duplicate", "unrecognized", "skipped"} and not self.note:
            raise ValueError(f"{self.path}: для «{self.classification}» нужен note с причиной")
        return self


class Lesson(Model):
    id: LessonId
    number: int = Field(ge=1)
    date: dt.date | None = None
    source_folder: str
    media: list[Media] = []
    files: list[LessonFile] = []

    @model_validator(mode="after")
    def _unique_file_paths(self) -> Lesson:
        seen: set[str] = set()
        for entry in self.files:
            if entry.path in seen:
                raise ValueError(f"файл {entry.path} повторяется в журнале")
            seen.add(entry.path)
        return self


class Section(Model):
    id: str
    name: str


class Topic(Model):
    id: TopicId
    name: str
    section: str


class TopicsFile(Model):
    sections: list[Section]
    topics: list[Topic] = []

    @model_validator(mode="after")
    def _consistent(self) -> TopicsFile:
        section_ids = {s.id for s in self.sections}
        seen: set[str] = set()
        for topic in self.topics:
            if topic.section not in section_ids:
                raise ValueError(f"тема «{topic.name}»: неизвестный раздел {topic.section}")
            key = topic.name.casefold()
            if key in seen:
                raise ValueError(f"имя темы «{topic.name}» повторяется")
            seen.add(key)
        return self


class FormatFile(Model):
    format_version: int


class Report(Model):
    id: ReportId
    element: Id
    item: int | None = None
    comment: str
    created: dt.datetime
    status: Literal["open", "fixed", "rejected"] = "open"
    resolution: str | None = None
    resolved: dt.datetime | None = None


# --- Элементы контента -----------------------------------------------------------------------


class ElementBase(Model):
    lesson: int | None = None
    part: Part | None = None
    topics: list[TopicId] = []
    origin: Origin
    sources: list[SourceRef] = []
    needs_review: NeedsReview = NeedsReview()

    @model_validator(mode="after")
    def _common_rules(self) -> ElementBase:
        if self.lesson is not None and self.part is None and getattr(self, "kind", None) != "vocab":
            raise ValueError("part обязательно, если указан lesson")
        if not self.topics and not self.needs_review.flag:
            raise ValueError("нужна хотя бы одна тема (topics) или пометка needs_review")
        if not self.sources and self.origin != "user":
            raise ValueError("sources обязательны, кроме элементов с origin: user")
        return self


class Theory(ElementBase):
    id: TheoryId
    kind: Literal["theory"]
    title: str
    body: str = ""


class Text(ElementBase):
    id: TextId
    kind: Literal["text"]
    title: str
    body: str = ""


class Instruction(Model):
    ru: str
    original: str
    original_lang: Literal["fr", "en", "ru"]
    origin: Origin = "ai"


class Links(Model):
    text: TextId | None = None
    theory: TheoryId | None = None


class ItemBase(Model):
    id: int = Field(ge=1)
    answers_origin: Origin | None = None
    needs_review: NeedsReview = NeedsReview()


class GapItem(ItemBase):
    text: str
    hint: str | None = None
    answers: dict[int, list[str]]

    @property
    def gaps(self) -> list[int]:
        return [int(n) for n in GAP_RE.findall(self.text)]

    @model_validator(mode="after")
    def _gaps_match_answers(self) -> GapItem:
        if sorted(self.gaps) != sorted(self.answers):
            raise ValueError(
                f"пункт {self.id}: пропуски {{{{N}}}} в тексте {sorted(self.gaps)} "
                f"не совпадают с ответами {sorted(self.answers)}"
            )
        if any(not variants for variants in self.answers.values()):
            raise ValueError(f"пункт {self.id}: у пропуска нет ни одного ответа")
        return self


class TransformItem(ItemBase):
    prompt: str
    answers: list[str] = Field(min_length=1)


class TrueFalseItem(ItemBase):
    statement: str
    answer: bool


class ChoiceItem(ItemBase):
    question: str
    options: list[str] = Field(min_length=2)
    answer: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def _indices_in_range(self) -> ChoiceItem:
        if any(i < 0 or i >= len(self.options) for i in self.answer):
            raise ValueError(f"пункт {self.id}: индекс ответа вне списка вариантов")
        return self


class TwoFormsItem(GapItem):
    forms: list[str] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _answer_is_form(self) -> TwoFormsItem:
        forms = {f.casefold() for f in self.forms}
        for variants in self.answers.values():
            if any(v.casefold() not in forms for v in variants):
                raise ValueError(f"пункт {self.id}: ответ должен быть одной из двух форм")
        return self


class GroupingItem(ItemBase):
    word: str
    answer: str


class PictureItem(ItemBase):
    prompt: str | None = None
    answers: list[str] = []


class OpenItem(ItemBase):
    prompt: str


class ExerciseBase(ElementBase):
    id: ExerciseId
    kind: Literal["exercise"]
    number: int = Field(ge=1)
    sheet_number: str | None = None
    description_ru: str
    instruction: Instruction
    status: Status = "main"
    reference: str | None = None
    links: Links = Links()
    show_source: bool = False
    answers_origin: Origin = "ai"


class GapChoiceExercise(ExerciseBase):
    type: Literal["gap_choice"]
    options: list[str] = Field(min_length=2)
    items: list[GapItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _answers_in_options(self) -> GapChoiceExercise:
        options = {o.casefold() for o in self.options}
        for item in self.items:
            for variants in item.answers.values():
                if any(v.casefold() not in options for v in variants):
                    raise ValueError(f"пункт {item.id}: ответ не входит в варианты options")
        return self


class GapInputExercise(ExerciseBase):
    type: Literal["gap_input"]
    items: list[GapItem] = Field(min_length=1)


class MultiGapExercise(ExerciseBase):
    type: Literal["multi_gap"]
    items: list[GapItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _two_gaps(self) -> MultiGapExercise:
        for item in self.items:
            if len(item.gaps) < 2:
                raise ValueError(f"пункт {item.id}: нужно не меньше 2 пропусков")
        return self


class TransformExercise(ExerciseBase):
    type: Literal["transform"]
    items: list[TransformItem] = Field(min_length=1)


class TrueFalseExercise(ExerciseBase):
    type: Literal["true_false"]
    items: list[TrueFalseItem] = Field(min_length=1)


class ChoiceExercise(ExerciseBase):
    type: Literal["choice"]
    items: list[ChoiceItem] = Field(min_length=1)


class TwoFormsExercise(ExerciseBase):
    type: Literal["two_forms"]
    items: list[TwoFormsItem] = Field(min_length=1)


class GroupingExercise(ExerciseBase):
    type: Literal["grouping"]
    groups: list[str] = Field(min_length=2)
    items: list[GroupingItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _answer_is_group(self) -> GroupingExercise:
        for item in self.items:
            if item.answer not in self.groups:
                raise ValueError(f"пункт {item.id}: ответ должен быть одной из групп")
        return self


class PictureExercise(ExerciseBase):
    type: Literal["picture"]
    items: list[PictureItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _shows_source(self) -> PictureExercise:
        if not self.show_source:
            raise ValueError("для упражнения «по картинке» нужно show_source: true")
        return self


class OpenExercise(ExerciseBase):
    type: Literal["open"]
    items: list[OpenItem] = Field(min_length=1)


Exercise = Annotated[
    GapChoiceExercise
    | GapInputExercise
    | MultiGapExercise
    | TransformExercise
    | TrueFalseExercise
    | ChoiceExercise
    | TwoFormsExercise
    | GroupingExercise
    | PictureExercise
    | OpenExercise,
    Field(discriminator="type"),
]

EXERCISE_TYPE_NAMES = {
    "gap_choice": "пропуск с выбором из списка",
    "gap_input": "пропуск со свободным вводом",
    "multi_gap": "несколько пропусков в предложении",
    "transform": "трансформация предложения",
    "true_false": "верно / неверно",
    "choice": "выбор варианта",
    "two_forms": "выбор из двух форм",
    "grouping": "распределение по группам",
    "picture": "по картинке",
    "open": "открытый ответ",
}


# --- Лексика ---------------------------------------------------------------------------------


class VocabFlags(Model):
    plural_only: bool = False
    h_aspire: bool = False
    irregular: bool = False
    reflexive: bool = False


class Translation(Model):
    text: str
    lesson: int | None = None
    origin: Origin


class Forms(Model):
    feminine: str | None = None
    plural: str | None = None
    note: str | None = None


class VerbInfo(Model):
    group: int | None = Field(default=None, ge=1, le=3)
    conjugation: dict[str, dict[str, str]] = {}


class Example(Model):
    text: str
    lesson: int | None = None


class VocabEntry(ElementBase):
    id: VocabId
    kind: Literal["vocab"]
    entry_type: Literal["word", "verb", "phrase"]
    text: str
    article: Literal["le", "la", "l'", "les"] | None = None
    gender: Literal["m", "f", "both"] | None = None
    flags: VocabFlags = VocabFlags()
    pos: str | None = None
    translations: list[Translation] = Field(min_length=1)
    forms: Forms = Forms()
    verb: VerbInfo | None = None
    lessons: list[int] = []
    examples: list[Example] = []
    notes: str | None = None
    needs_completion: bool = False

    @model_validator(mode="after")
    def _no_lesson_part(self) -> VocabEntry:
        if self.lesson is not None or self.part is not None:
            raise ValueError("у лексики нет lesson/part — связь с уроками через lessons")
        return self


Element = Theory | Text | ExerciseBase | VocabEntry
