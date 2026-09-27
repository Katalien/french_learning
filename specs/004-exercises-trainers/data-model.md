# Data Model: Упражнения с автопроверкой и тренажёры

Два вида данных, как в 003: **контент** (YAML в приватном хранилище, формат v1 с
дополнениями) и **прогресс** (SQLite `CONTENT_DIR/.progress/progress.sqlite`, схема v2).

## Контент (приватное хранилище)

### Упражнение (001, без изменений формата)

Поле `status` (`main` / `optional` / `reserve`) теперь меняется из интерфейса (R7).

### Каталог тренажёров — `trainers.yaml` (новый, необязательный)

```yaml
trainers:
  - id: negation                 # slug: ^[a-z][a-z0-9-]{2,40}$, уникален
    name: Отрицание
    description: ne … pas, ne … jamais, ne … plus в настоящем времени
    source: agent                # agent | builtin (для переопределения встроенного)
    exercise_type: transform     # gap_input | gap_choice | transform | choice | two_forms | true_false
    progress: stats              # stats (для agent); srs — только встроенные
    rules: |                     # правила для агента: что и как генерировать
      Утвердительное предложение → отрицательное. Лексика — из словаря, …
    origin: ai                   # кто создал запись (I)
  - id: articles                 # переопределение встроенного: только source
    source: agent
    rules: |
      Артикли в контексте предложения …
```

Проверки: `id` уникален; для встроенного id допустимы только поля `source` и `rules`;
`exercise_type` — из перечня, который поддерживает выполнение пакетов.

### Пакет заданий — `trainers/<trainer_id>/tb-xxxxxxxx.yaml` (новый)

```yaml
id: tb-k2m4q7xa
kind: task_batch
trainer: negation
type: transform                 # как у упражнения; options — для gap_choice / two_forms
created: 2026-10-01T18:20:00
origin: ai
instruction_ru: Сделайте предложение отрицательным.
items:                          # модели пунктов упражнений 001 + new_words
  - id: 1
    prompt: Je mange du pain.
    answers: ["Je ne mange pas de pain."]
    new_words: []               # ≤ 2: [{text: "le beurre", translation: "масло"}]
    needs_review: {flag: false}
```

Проверки: `trainer` есть в каталоге; тип совпадает с `exercise_type` тренажёра; у пункта
`new_words` не больше 2; ответы — по правилам моделей пунктов 001. Файл после создания
не меняется, кроме исправлений по сообщениям об ошибках (`/fix-reports`).

### Сообщение об ошибке (001, расширение)

`element` может ссылаться на пакет (`tb-…`); `item` — номер задания. Префикс `tb` добавлен
в шаблон идентификаторов (`Id`, `new-ids`).

## Прогресс (SQLite, схема v2; миграция v1 → v2 добавляет таблицы)

### `exercise_attempts` — попытки упражнений уроков

| Поле | Тип | Смысл |
|---|---|---|
| id | integer pk | |
| exercise_id | text | `ex-…` |
| scope | text | `full` — всё упражнение; `item` — один пункт из «Моих ошибок» |
| item_ids | text (json) | пункты попытки (для `full` — все) |
| status | text | `draft` → `checked` (для открытого ответа — `saved`) |
| answers | text (json) | `{item_id: {gap: ответ}}`; у choice — список индексов, у true_false — bool |
| first_results | text (json) | `{item_id: "correct" \| "wrong"}` — фиксируется при первой проверке пункта |
| current_results | text (json) | `{item_id: {gap: "correct" \| "wrong" \| "choose"}}` — последняя проверка |
| marks | text (json) | `{item_id: "fixed_self" \| "revealed"}` |
| created_at, checked_at, updated_at | text (ISO) | |

Переходы: `draft` (автосохранение) → `checked` (первое «Проверить»). Потом можно
исправлять и проверять снова (меняются `answers`, `current_results`, `marks`; `first_results`
только дополняется пунктами, отложенными выбором написания). «Решить заново» создаёт новую
попытку `draft`. Удаления нет (VII). Итог «пересчитано» вычисляется при чтении (R4).

### `trainer_cards` — расписание вопросов встроенных тренажёров

| Поле | Тип | Смысл |
|---|---|---|
| trainer_id | text | `articles`, `numbers`, … |
| key | text | стабильный ключ вопроса (R10) |
| fsrs | text (json) | состояние FSRS |
| due | text (ISO) | |
| created_at | text | |
| pk | (trainer_id, key) | |

### `trainer_answers` — все ответы в тренажёрах (встроенных и пакетах)

| Поле | Тип | Смысл |
|---|---|---|
| id | integer pk | |
| trainer_id | text | |
| key | text | ключ вопроса или `tb-…:N` для задания пакета |
| answer | text | что ввёл пользователь |
| correct | integer | 1 / 0 |
| revealed | integer | подсмотрен ответ (считается ошибкой) |
| answered_at | text | |
| session_id | text | |

Производные: архив пакетов — ключи с `correct = 1`; пул — задания минус архив; «Ошибки»
тренажёра — задания пула, на которые хотя бы раз ответили неверно; статистика — доля верных
по дням, частые ошибки (одинаковые неверные ответы на один ключ).

### `trainer_sessions` — подход к тренажёру

| Поле | Тип | Смысл |
|---|---|---|
| id | text pk | |
| trainer_id | text | |
| params | text (json) | набор данных (весь словарь / урок / тема / сложные), для пакетов — только пул |
| queue | text (json) | ключи вопросов порции |
| position | integer | |
| correct | integer | верных в порции (для итога «18 из 20») |
| created_at | text | |

### `settings`

Добавлена настройка `trainer_portion_size` (по умолчанию 20).

## Вычисляемые сущности (без хранения)

- **Вопрос тренажёра**: ключ, текст задания, подсказка, допустимые ответы, способ ответа
  (`buttons` с вариантами / `input` / `order` для «собери предложение»).
- **Каталог**: встроенные + `trainers.yaml`.
- **Прогресс урока**: `ExerciseProgress.is_done(exercise_id)`.
