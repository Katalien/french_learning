# Data Model: 011

Формат контента не меняется. База прогресса — схема **v5** (одна новая таблица).

## Оценка карточки (`reviews.rating`)

`again` | `hard` | `good` | **`article`** (новое: «Ошибка в артикле»). `article` → FSRS `Good`.
В «сложных» не учитывается ни как ошибка, ни как успех.

## `trainer_priority` (новая таблица, v5)

| Поле | Тип | Смысл |
|---|---|---|
| `trainer_id` | text | `articles` |
| `key` | text | `articles:<entry_id>:def` / `:indef` |
| `review_id` | integer | оценка `article`, создавшая приоритет (для отмены) |
| `created_at` | text | порядок — раньше добавлено, раньше в очереди |

Ключ `(trainer_id, key)` уникален (повторное добавление обновляет `review_id`, `created_at`).
Строка удаляется: ответом на этот вопрос в тренажёре; отменой оценки `review_id`.

## Сеанс повторения (`sessions.params`, JSON)

`SessionParams.drill: bool = False` — тренировка без записи. В `state["drill"]` — список
оценок тренировки `[[entry_id, direction, rating], …]`; `summary` тренировки — из него.

## Вопрос карточки

`Question.lines: list[str]` — переводы по отдельности (для ru_fr); `text` остаётся для поиска
и совместимости.
