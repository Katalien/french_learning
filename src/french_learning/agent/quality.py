"""Чек-лист для ручной сверки качества работы агента (SC-005).

В список попадают пункты упражнений, в которых агент был уверен (без «требует проверки»);
пользователь сверяет их с оригиналами и считает ошибки. Допустимо не больше 5%.
"""

from __future__ import annotations

from pathlib import Path

from french_learning.content.index import ContentIndex
from french_learning.content.loader import load_content
from french_learning.content.schema import GAP_RE

PART_NAMES = {"class": "в классе", "homework": "домашка"}


def _fill(text: str, answers: dict[int, list[str]]) -> str:
    return GAP_RE.sub(lambda m: "[" + " / ".join(answers.get(int(m.group(1)), ["?"])) + "]", text)


def _render(exercise, item) -> str | None:
    kind = exercise.type
    if kind in {"gap_choice", "gap_input", "multi_gap", "two_forms"}:
        return _fill(item.text, item.answers)
    if kind == "transform":
        return f"{item.prompt} → {' | '.join(item.answers)}"
    if kind == "true_false":
        return f"{item.statement} → {'верно' if item.answer else 'неверно'}"
    if kind == "choice":
        return f"{item.question} → {' / '.join(item.options[i] for i in item.answer)}"
    if kind == "grouping":
        return f"{item.word} → {item.answer}"
    if kind == "picture" and item.answers:
        return f"{item.prompt or ''} → {' | '.join(item.answers)}".strip()
    return None  # открытый ответ и «по картинке» без ответов не сверяются


def quality_sample(root: Path, lessons: list[int]) -> str:
    index = ContentIndex(load_content(root))
    lines = [f"# Сверка качества: уроки {', '.join(map(str, lessons))}", ""]
    lines += [
        "Сверьте каждый пункт с оригиналом. Ошибка — неверно распознанный текст или неверный",
        "ответ. Отметьте [x] проверенные и запишите число ошибок.",
        "",
    ]
    total = 0
    for number in lessons:
        for exercise in index.elements(number, kind="exercise"):
            if exercise.needs_review.flag:
                continue
            source = next((s.file for s in exercise.sources if s.file), "—")
            for item in exercise.items:
                if item.needs_review.flag:
                    continue
                rendered = _render(exercise, item)
                if rendered is None:
                    continue
                total += 1
                lines.append(
                    f"- [ ] Урок {number} · {PART_NAMES[exercise.part]} · упр. {exercise.number} "
                    f"· пункт {item.id}: {rendered} — `{source}`"
                )
    lines += ["", f"Пунктов для сверки: {total}, допустимо ошибок: {total * 5 // 100}"]
    return "\n".join(lines)
