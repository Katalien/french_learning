"""Данные для навыков тренажёров: каталог, контекст генерации, ошибки (contracts/cli.md 004)."""

from __future__ import annotations

from pathlib import Path

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.exercises.grading import correct_answers
from french_learning.practice.db import ProgressDB
from french_learning.trainers.catalog import catalog, get_trainer
from french_learning.trainers.pools import all_tasks, pool_mistakes, pool_questions
from french_learning.trainers.schedule import TrainerSchedule

MAX_NEW_WORDS = 2


class TrainerNotFound(Exception):
    pass


def _index(root: Path) -> ContentIndex:
    return ContentIndex(load_content(root))


def trainers_list(root: Path) -> list[dict]:
    index = _index(root)
    db = ProgressDB(root)
    try:
        schedule = TrainerSchedule(db)
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "source": t.source,
                "builtin": t.builtin,
                "exercise_type": t.exercise_type,
                "rules": t.rules,
                "in_pool": len(pool_questions(index, schedule, t.id))
                if t.source == "agent"
                else None,
            }
            for t in catalog(index)
        ]
    finally:
        db.close()


def trainer_context(root: Path, trainer_id: str) -> dict:
    index = _index(root)
    trainer = get_trainer(index, trainer_id)
    if trainer is None:
        raise TrainerNotFound(
            f"тренажёра {trainer_id} нет в каталоге — сначала добавьте его: /add-trainer"
        )
    vocabulary = [
        {
            "text": e.text,
            "article": e.article,
            "gender": e.gender,
            "pos": e.pos,
            "translations": [t.text for t in e.translations],
            "lessons": e.lessons,
        }
        for e in index.content.elements.values()
        if e.kind == "vocab" and not e.hidden
    ]
    lessons = [
        {
            "number": lesson.number,
            "date": lesson.date,
            "topics": [t.name for t in index.lesson_topics(lesson.number)],
            "theory": [e.title for e in index.elements(lesson.number, kind="theory")],
        }
        for lesson in index.lessons()
    ]
    return {
        "trainer": {
            "id": trainer.id,
            "name": trainer.name,
            "description": trainer.description,
            "exercise_type": trainer.exercise_type,
            "rules": trainer.rules,
        },
        "vocabulary": sorted(vocabulary, key=lambda v: v["text"].casefold()),
        "lessons": lessons,
        "existing_tasks": [q.prompt for q in all_tasks(index, trainer.id)],
        "limits": {"max_new_words_per_item": MAX_NEW_WORDS},
        "batch_folder": f"trainers/{trainer.id}/",
    }


def mistakes_list(root: Path, trainer_id: str | None, lesson: int | None) -> dict:
    from french_learning.exercises.attempts import AttemptStore
    from french_learning.exercises.mistakes import find_mistakes

    index = _index(root)
    db = ProgressDB(root)
    try:
        result: dict = {}
        if trainer_id:
            schedule = TrainerSchedule(db)
            result["trainer"] = [
                {
                    "task": m["question"].key,
                    "instruction": m["question"].instruction,
                    "prompt": m["question"].prompt,
                    "answers": m["answers"],
                    "correct": m["question"].answers
                    or [" / ".join(v) for v in m["question"].gaps.values()],
                }
                for m in pool_mistakes(index, schedule, trainer_id)
            ]
        if lesson is not None or not trainer_id:
            result["lessons"] = [
                {
                    "exercise": m.exercise.id,
                    "lesson": m.exercise.lesson,
                    "number": m.exercise.number,
                    "instruction": m.exercise.instruction.ru,
                    "item": m.item.id,
                    "answer": [v for k, v in m.answer.items() if not k.endswith("~choice")],
                    "correct": [
                        " / ".join(v) for v in correct_answers(m.exercise, m.item).values()
                    ],
                }
                for m in find_mistakes(index, AttemptStore(db), lesson=lesson)
            ]
        return result
    finally:
        db.close()
