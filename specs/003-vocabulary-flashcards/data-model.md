# Data Model: Словарь и карточки

## Контент (файлы) — дополнение формата v1

`VocabEntry` (001) + необязательные поля:
- `hidden: bool` (по умолчанию `false`) — запись из урока скрыта пользователем;
- `completed_by_ai: list[str]` — поля, заполненные агентом (`gender`, `article`, `forms`,
  `verb`, `pos`) — для происхождения (I).

Правила «одно слово — одна запись» и накопления переводов — как в 002 (FR-021, FR-021a).

## Прогресс (SQLite, `CONTENT_DIR/.progress/progress.sqlite`)

### `meta`
`key` TEXT PK, `value` TEXT — `schema_version`, `last_backup_date`, `last_backup_pushed`.

### `settings`
`key` TEXT PK, `value` TEXT — `portion_size` (по умолчанию 20), `directions`
(`staged` | `both`, по умолчанию `staged`).

### `cards`
| Поле | Тип | Правила |
|---|---|---|
| `entry_id` | TEXT | id записи словаря |
| `direction` | TEXT | `fr_ru` / `ru_fr` |
| `fsrs` | TEXT (JSON) | состояние FSRS (due, stability, difficulty, state, reps, lapses, last_review) |
| `due` | TEXT (ISO datetime) | копия для выборки «пора сегодня» |
| `suspended` | INTEGER | 1 — «Я это знаю» |
| `created_at` | TEXT | |

PK (`entry_id`, `direction`). Карточка без оценок — «новая» (due = момент создания).

### `reviews` — история (не удаляется)
| Поле | Тип |
|---|---|
| `id` | INTEGER PK |
| `entry_id`, `direction` | TEXT |
| `rating` | TEXT: `again` / `hard` / `good` |
| `method` | TEXT: `self` / `input` |
| `mode` | TEXT: `today` / `lesson` / `topic` / `all` / `hard` |
| `answer` | TEXT? (введённый ответ) |
| `reviewed_at` | TEXT |
| `session_id` | TEXT |
| `prev_fsrs` | TEXT (JSON) — снимок для отмены |

### `sessions`
`id` TEXT PK, `params` JSON (режим, вид, направление, урок / тема, способ, источник:
`lesson` / `dictionary`), `queue` JSON (список [entry_id, direction]), `position` INTEGER,
`created_at`, `last_review_id` INTEGER?.

## Переходы состояния карточки

- новая / любая → оценка → FSRS пересчитывает `fsrs`, `due`; оценка пишется в `reviews`;
- первая оценка «Помню» в `fr_ru` при `directions = staged` → создаётся карточка `ru_fr`;
- «Я это знаю» → `suspended = 1`; «Вернуть» → `0`;
- «Отменить последнюю оценку» (только последнюю в текущем сеансе) → `fsrs` ← `prev_fsrs`,
  запись оценки удаляется, позиция сеанса − 1.

## Вычисляемое

- «Пора сегодня»: не приостановленные карточки с `due` ≤ конец сегодняшнего дня + новые
  (без ограничения, FR-035), направление по выбору.
- «Сложные» (research R10): среди последних 5 оценок записи «again» > «good».
- «Нужно дополнить»: `needs_completion: true` в файле записи.
