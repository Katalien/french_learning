# Contract: перевод и добавление из текста (006)

Только локально (принцип XII). Ошибки — `{"error": "…"}`.

## `GET /translate?q=<выделенное>`

`200` + объект из data-model («Результат перевода») — всегда, даже если перевода нет
(`translation: null`, `error`). `422` — пустой `q` или в нём кириллица.

Во внешний сервис уходит только `q` (и его начальная форма), ничего больше (FR-008).

## `POST /vocab/from-text` (JSON)

```json
{"text": "achètent", "sentence": "Elles achètent des pommes, du fromage et une baguette.", "lesson": 15}
```

- `201` + `{"id": "voc-…", "text": "acheter", "translation": "покупать", "merged": false}`
- `merged: true` — такая запись уже была, дополнена (пример), дубль не создан
- `422` — абзац, пусто, кириллица, перевода нет
- запись в хранилище контента — через `ContentWriter` (коммит, как любые правки словаря)

## `POST /settings/translate` (форма из меню «⋯»)

`show=0|1` → cookie `translate`, редирект обратно (как `/settings/origin`).

## `POST /settings/translator` (форма «Настройки»)

`translator=mymemory|deepl`, `mymemory_email=` → настройки базы прогресса. DeepL без ключа
в окружении → ошибка «ключ DeepL не задан» и выбор не меняется.

## `POST /settings/translations/clear`

Очистить запас переводов → редирект с сообщением «Очищено: N».
