# Data Model: Заметки (005)

## База прогресса — схема v3

Добавляется одна таблица, остальные не меняются. `SCHEMA_VERSION = 3`.

```sql
create table if not exists notes (
    id integer primary key autoincrement,
    kind text not null check (kind in ('note', 'question')),
    body text not null check (length(trim(body)) > 0),
    important integer not null default 0,
    answered integer not null default 0,      -- только для kind = 'question'
    answer text,                              -- только для kind = 'question'
    lesson integer not null,                  -- номер урока (всегда)
    element_id text,                          -- null → заметка ко всему уроку
    element_title text,                       -- копия названия элемента (для «было: …»)
    anchor text,                              -- JSON якоря или null (заметка ко всему элементу)
    created_at text not null,
    updated_at text not null
);
create index if not exists notes_lesson on notes (lesson, element_id);
create index if not exists notes_open_questions on notes (kind, answered);
```

### Якорь (`anchor`, JSON)

| поле | тип | смысл |
|---|---|---|
| `exact` | str (1–500) | выделенный текст (пробелы сжаты) |
| `prefix` | str (0–32) | текст слева от выделения |
| `suffix` | str (0–32) | текст справа от выделения |
| `start` | int ≥ 0 | смещение в тексте контейнера на момент создания |

## Сущность `Note` (`notes/store.py`)

| поле | тип | правила |
|---|---|---|
| `id` | int | |
| `kind` | `note` \| `question` | |
| `body` | str | непустой после `strip()`, до 2000 символов |
| `important` | bool | |
| `answered` | bool | `False` у `note`; `True`, если записан непустой `answer` |
| `answer` | str \| None | только у `question`; пустая строка → `None` |
| `lesson` | int | для элемента — берётся из индекса контента, не от клиента |
| `element_id` | str \| None | элемент урока (text / theory / exercise); дополнительные материалы запрещены |
| `element_title` | str \| None | заполняется сервером при создании |
| `anchor` | Anchor \| None | только вместе с `element_id` |
| `created_at`, `updated_at` | ISO-время | |
| `origin` | всегда `user` | вычисляемое поле (принцип I), не хранится |

### Переходы вопроса

```text
open (answered=0) ──✓ / ответ записан──► answered (answered=1, answer может быть пустым)
answered ──снять ✓──► open (answer сохраняется)
```

Смена `kind`: `question` → `note` сбрасывает `answered` (ответ остаётся в `answer`,
но не показывается); `note` → `question` делает вопрос открытым.

## Выборки (методы `NoteStore`)

| метод | что возвращает |
|---|---|
| `for_elements(ids)` | заметки элементов для страницы (JSON для `notes.js`) |
| `for_lesson(n)` | все заметки урока |
| `open_questions()` | открытые вопросы всех уроков: сначала новые уроки, внутри — по времени |
| `open_questions_count()` | число для «❓ N» |
| `lesson_counts()` | `{урок: число заметок}` для боковой панели |
| `create / update / delete` | изменения с проверками выше |

## Страница «Заметки к уроку» — группировка (`notes/grouping.py`)

- **Вопросы**: открытые вопросы урока (сначала созданные раньше), затем отвеченные — они
  свёрнуты.
- **К уроку**: пометки без `element_id` и пометки элементов, которых больше нет в уроке
  (с пометкой «было: `element_title`»).
- **Блоки элементов**: элементы урока в порядке урока (теория → тексты → задания класса →
  домашние → резерв, как в `lesson_tree`). Блок есть, только если у элемента есть пометки.
  Внутри — сначала заметки ко всему элементу, затем к фрагментам, по времени создания.

Группировка — чистая функция от заметок и дерева урока, её проверяют юнит-тесты.
