# Data Model: Чтение с переводом (006)

## База прогресса — схема v4

```sql
create table if not exists translations (
    key text not null,              -- нормализованный французский текст
    direction text not null,        -- 'fr-ru'
    text text not null,             -- перевод
    service text not null,          -- 'mymemory' | 'deepl'
    created_at text not null,
    primary key (key, direction)
);
```

Настройки (`settings`, не секреты):

| ключ | значения | по умолчанию |
|---|---|---|
| `translator` | `mymemory` \| `deepl` | `mymemory` |
| `mymemory_email` | почта или пусто | пусто (не передаётся) |

Ключ DeepL — только `DEEPL_API_KEY` в `.env` / окружении (`Settings.deepl_api_key`),
никогда в базе и контенте (research R3).

Cookie браузера: `translate` = `0` / `1` (по умолчанию включён).

## Нормализация ключа (`translate/normalize.py`)

`casefold` → `’` и `ʼ` в `'` → пробелы сжать → обрезать края и конечные `.,;:!?…»«"`.
Функция одна для запаса, поиска в словаре и проверки на дубль.

## Результат перевода (`translate/service.py` → JSON `/translate`)

| поле | тип | смысл |
|---|---|---|
| `text` | str | выделенное (как пришло) |
| `translation` | str \| null | перевод; null — недоступен |
| `source` | `dictionary` \| `cache` \| `service` \| `none` | откуда перевод |
| `error` | str \| null | «Перевод сейчас недоступен», «Выделите меньше (до 500 символов)» |
| `lemma` | str \| null | начальная форма, если отличается от выделенного (одно слово) |
| `lemma_translation` | str \| null | перевод начальной формы (словарь → запас → сервис) |
| `entry` | `{id, translation}` \| null | запись словаря, если уже есть (в т. ч. скрытая) |
| `can_add` | bool | не абзац, есть перевод, записи ещё нет |
| `add_as` | `{text, entry_type}` | что добавит «+ В словарь»: форма и вид (word / verb / phrase) |

Порядок поиска (FR-006): словарь (по выделенному и по форме) → запас → сервис. Ответ сервиса
пишется в запас; ошибки не пишутся.

## Добавление в словарь (`POST /vocab/from-text`)

Вход: `text` (выделенное), `sentence` (предложение вокруг), `lesson` (если есть).
Сервер заново получает перевод (из запаса — без сервиса) и вызывает
`VocabEditor.add_word(..., example=Example(text=sentence, lesson=lesson),
translation_origin=<service|user>)`:

| поле записи | значение |
|---|---|
| `entry_type` | `add_as.entry_type` |
| `text` | `add_as.text` (форма или фраза как есть) |
| `translations[0]` | `{text, lesson?, origin: "service"}` (если перевод из запаса/сервиса) |
| `examples` | `[{text: sentence, lesson?}]`; у предложения, добавленного фразой, — не дублируется |
| `topics` | `[]` (без темы) |
| `lessons` | не заполняется (research R7) |
| `needs_completion` | true для word / verb |
| `origin` | `user` |
