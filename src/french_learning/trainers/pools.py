"""Пул заданий от агента (FR-050b–FR-053; research R9 функции 004).

Задания — пункты пакетов `trainers/<id>/tb-*.yaml`. Что решено, хранится только в базе
прогресса: задание в архиве, если на него хоть раз ответили верно; остальные — в пуле.
«Ошибки» — задания пула, на которые уже отвечали неверно. Статистика — по всем ответам.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from french_learning.content.index import ContentIndex
from french_learning.content.schema import GAP_RE
from french_learning.trainers.questions import Question
from french_learning.trainers.schedule import TrainerSchedule

TF = {True: "верно", False: "неверно"}


def _hint(item: Any) -> str | None:
    if not getattr(item, "new_words", None):
        return getattr(item, "hint", None)
    words = "; ".join(f"{w.text} — {w.translation}" for w in item.new_words)
    base = getattr(item, "hint", None)
    return f"{base} · Новые слова: {words}" if base else f"Новые слова: {words}"


def task_question(batch: Any, item: Any) -> Question:
    """Пункт пакета → вопрос тренажёра с тем же механизмом ответа, что у встроенных."""
    common = {
        "key": f"{batch.id}:{item.id}",
        "hint": _hint(item),
        "instruction": batch.instruction_ru,
        "review_note": item.needs_review.note if item.needs_review.flag else None,
        "source": batch.id,
    }
    kind = batch.type
    if kind in ("gap_input", "gap_choice", "multi_gap", "two_forms"):
        gaps = {str(g): list(v) for g, v in item.answers.items()}
        if len(gaps) > 1:
            return Question(prompt=item.text, answers=[], mode="gaps", gaps=gaps, **common)
        [(gap, answers)] = gaps.items()
        prompt = GAP_RE.sub("___", item.text)
        full = item.text.replace(f"{{{{{gap}}}}}", answers[0])
        if kind in ("gap_choice", "two_forms"):
            options = batch.options if kind == "gap_choice" else item.forms
            return Question(
                prompt=prompt,
                answers=answers,
                mode="buttons",
                options=list(options),
                full=full,
                **common,
            )
        return Question(prompt=prompt, answers=answers, full=full, **common)
    if kind == "transform":
        return Question(prompt=item.prompt, answers=list(item.answers), **common)
    if kind == "true_false":
        return Question(
            prompt=item.statement,
            answers=[TF[item.answer]],
            mode="buttons",
            options=[TF[True], TF[False]],
            **common,
        )
    # choice
    answers = [item.options[i] for i in item.answer]
    return Question(
        prompt=item.question, answers=answers, mode="buttons", options=list(item.options), **common
    )


def all_tasks(index: ContentIndex, trainer_id: str) -> list[Question]:
    return [task_question(b, i) for b in index.batches(trainer_id) for i in b.items]


def _answers(schedule: TrainerSchedule, trainer_id: str) -> dict[str, list[dict]]:
    by_key: dict[str, list[dict]] = {}
    for row in schedule.history(trainer_id):
        by_key.setdefault(row["key"], []).append(row)
    return by_key


def pool_questions(
    index: ContentIndex, schedule: TrainerSchedule, trainer_id: str
) -> list[Question]:
    answered = _answers(schedule, trainer_id)
    return [
        q
        for q in all_tasks(index, trainer_id)
        if not any(r["correct"] for r in answered.get(q.key, []))
    ]


def pool_mistakes(index: ContentIndex, schedule: TrainerSchedule, trainer_id: str) -> list[dict]:
    answered = _answers(schedule, trainer_id)
    return [
        {"question": q, "answers": [r["answer"] for r in answered[q.key] if r["answer"]]}
        for q in pool_questions(index, schedule, trainer_id)
        if answered.get(q.key)
    ]


def pool_summary(index: ContentIndex, schedule: TrainerSchedule, trainer_id: str) -> dict:
    total = len(all_tasks(index, trainer_id))
    in_pool = len(pool_questions(index, schedule, trainer_id))
    return {
        "in_pool": in_pool,
        "archived": total - in_pool,
        "mistakes": len(pool_mistakes(index, schedule, trainer_id)),
        "total": total,
    }


def pool_stats(index: ContentIndex, schedule: TrainerSchedule, trainer_id: str) -> dict:
    rows = schedule.history(trainer_id)
    correct = sum(r["correct"] for r in rows)
    days: dict[str, dict] = {}
    for r in rows:
        day = days.setdefault(r["answered_at"][:10], {"answers": 0, "correct": 0})
        day["answers"] += 1
        day["correct"] += r["correct"]
    wrong = Counter((r["key"], r["answer"]) for r in rows if not r["correct"] and r["answer"])
    questions = {q.key: q for q in all_tasks(index, trainer_id)}
    typical = [
        {"question": questions.get(key), "answer": answer, "count": count}
        for (key, answer), count in wrong.most_common(10)
        if count >= 2
    ]
    return {
        "answers": len(rows),
        "correct": correct,
        "percent": round(100 * correct / len(rows)) if rows else 0,
        "days": [
            {"date": d, **v, "percent": round(100 * v["correct"] / v["answers"])}
            for d, v in sorted(days.items())
        ],
        "typical": typical,
    }
