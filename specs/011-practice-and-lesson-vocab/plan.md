# Implementation Plan: Повторение и лексика урока

**Branch**: `011-practice-and-lesson-vocab` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

## Summary

Пять правок вокруг повторения слов:
- в настройке повторения — только темы со словами (R1);
- оценка «Ошибка в артикле» для существительных в ru→fr: слово как «Помню», вопросы слова —
  в начало тренажёра «Артикли», отмена работает (R2, таблица `trainer_priority`, схема v5);
- переводы на карточке — по строке, меньше шрифт при большом объёме (R3);
- на итоге сеанса — повтор-тренировка «Не помню» / «Не помню + С трудом» без записи (R4);
- фильтры «Тема» / «Вид» в лексике урока, листание по отфильтрованному списку (R5).

## Technical Context

**Language/Version**: Python 3.12 (uv) · **Dependencies**: без новых · **Storage**: база
прогресса v5 (`trainer_priority`), формат контента не меняется · **Testing**: pytest, TDD —
оценка `article` (расписание, история, «сложные», отмена), приоритет тренажёра (порядок,
снятие ответом), тренировка (без записи, итог, кнопки), фильтры урока и соседи, темы в
настройке, разметка переводов · **Target**: браузер компьютера и 375 px ·
**Constraints**: прогресс не теряется; тренировка ничего не пишет в историю (VII не задет).

## Constitution Check

| Принцип | Как соблюдается | Статус |
|---|---|---|
| I. Прослеживаемость | Контент не меняется | ✅ |
| VI. Разделение данных | Новая таблица — в базе прогресса (не в git кода) | ✅ |
| VII. Сохранность истории | Оценки пишутся как раньше; тренировка ничего не удаляет; миграция только добавляет таблицу | ✅ |
| IX. Без внешних сервисов | Всё локально | ✅ |
| XI. Простота | Правки в существующих модулях, одна таблица | ✅ |
| XIII. TDD | Тесты до кода по каждой истории | ✅ |

## Project Structure

```text
specs/011-practice-and-lesson-vocab/ spec · plan · research · data-model · quickstart · contracts/ui-routes.md · tasks
src/french_learning/
├── practice/db.py                 # схема v5: trainer_priority
├── vocab/cards.py                 # оценка article, hard_ids, undo + снятие приоритета
├── vocab/entries.py               # Question.lines; признак «существительное с родом»
├── vocab/sessions.py              # drill: тренировка без записи, итог, слова для повтора
├── trainers/schedule.py           # приоритет в select, снятие ответом
├── web/routes/vocab.py            # rate article, drill, темы со словами, фильтры урока в соседях
├── web/routes/lessons.py          # фильтры лексики урока
├── web/templates/vocab/practice_card.html · practice_result.html · practice_summary.html
├── web/templates/lesson_vocab.html · partials/vocab_list.html
└── web/static/css/screens.css     # tr-line, tr-m, tr-s, кнопка артикля
tests/ — unit/vocab/test_cards.py · test_sessions.py · unit/trainers/test_schedule.py ·
integration/test_vocab_practice.py · test_vocab_pages.py · test_trainers_builtin.py
```

## Complexity Tracking

Отступлений нет. Схема базы v4 → v5 (только новая таблица, `create table if not exists`).
