---

description: "Задачи реализации функции 006 — чтение с переводом"
---

# Tasks: Чтение с переводом

**Input**: `specs/006-reader/` — spec.md, plan.md, research.md, data-model.md,
contracts/translate-api.md, contracts/ui-routes.md, quickstart.md, mockups/index.html

**Tests**: ОБЯЗАТЕЛЬНЫ для логики перевода, запаса, форм, добавления, маршрутов, миграции
и разметки (XIII). Внешние сервисы в тестах подменяются — настоящих запросов нет. JS —
по quickstart.md на демо-хранилище (порт 8010).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Добавить зависимость `simplemma` (`uv add simplemma`) — согласие пользователя на скачивание (19 МБ, MIT) получено 2026-09-30; пакет `src/french_learning/translate/`, тесты `tests/unit/translate/`
- [X] T002 `config.py`: `deepl_api_key: str | None` (из `DEEPL_API_KEY` / `.env`); `.env.example` — строка с пояснением

---

## Phase 2: Foundational — нормализация, запас, сервисы, формы

- [X] T003 [P] Тесты `test_normalize.py`: ключ (регистр, апострофы, пробелы, конечная пунктуация); кириллица; «больше одного предложения»; длина > 500
- [X] T004 `translate/normalize.py` — тесты T003 проходят
- [X] T005 [P] Тесты `tests/unit/practice/test_db.py`: схема 4, таблица `translations`, миграция 3 → 4 с сохранением заметок и карточек; настройки `translator` = `mymemory` по умолчанию
- [X] T006 `practice/db.py` — схема 4 — тесты T005 проходят
- [X] T007 [P] Тесты `test_providers.py`: разбор ответа MyMemory (успех, `MYMEMORY WARNING`, 403/429, пустой), DeepL (успех, 403, 456), тайм-аут/сеть → `TranslationUnavailable`; в запрос уходит только текст (и почта, если задана); DeepL без ключа — ошибка настройки. Сеть подменяется (`urllib.request.urlopen`)
- [X] T008 `translate/providers.py` — тесты T007 проходят
- [X] T009 [P] Тесты `test_lemma.py`: `achètent → acheter` (verb), `pommes → pomme` (word), `maison` без формы, несколько слов → phrase как есть
- [X] T010 `translate/lemma.py` — тесты T009 проходят
- [X] T011 [P] Тесты `test_service.py`: порядок словарь (по тексту и по форме, скрытые тоже) → запас → сервис; ответ сервиса пишется в запас один раз; ошибка не пишется; повтор не вызывает сервис; `can_add` / `add_as` / `entry`; перевод начальной формы; `clear()` и `count()` запаса
- [X] T012 `translate/cache.py`, `translate/service.py` — тесты T011 проходят

**Checkpoint**: перевод получается и запоминается без интерфейса.

---

## Phase 3: User Story 1 — перевод выделенного (P1) 🎯

- [X] T013 [P] [US1] Тесты `tests/integration/test_translate.py`: `GET /translate` — из словаря, из запаса, из (подменённого) сервиса, «недоступен», кириллица → 422, пусто → 422, > 500 → error; внешний сервис получает только `q`
- [X] T014 [US1] `web/routes/translate.py` (`/translate`), подключение сервиса в `app.state` — тесты T013 проходят
- [X] T015 [P] [US1] Тесты разметки: `data-translate` на теории, упражнении, доп. материале, словаре, карточке, теме, тренажёре; `<html data-translate="1">` по умолчанию и `"0"` при cookie; `translate.js` подключён
- [X] T016 [US1] Шаблоны: `data-translate` на французских блоках; `base.html` — атрибут и скрипт — тесты T015 проходят
- [X] T017 [US1] `selection.js`: зоны `[data-note-container], [data-translate], [lang="fr"]`, `ctx.zone` / `ctx.noteContainer`, ✕ в подсказке; `notes.js` — секция 005 по `ctx.noteContainer` (регрессия 005 — quickstart 005 §1 и вкладки урока «Тексты» / «Теория» из 0.6.1: кнопки заметок у каждого элемента, поле справа)
- [X] T018 [US1] `static/js/translate.js`: секция перевода по макету (загрузка → перевод, форма, 🔊 `data-speak`, сообщения), стили подсказки; без перевода при кириллице и выключенном переключателе
- [X] T019 [US1] Проверка quickstart §1

---

## Phase 4: User Story 2 — в словарь (P1)

- [ ] T020 [P] [US2] Тесты `tests/unit/vocab/test_edits.py`: `add_word(example=…, translation_origin="service")` — пример с уроком, перевод с `origin: service` и уроком, `lessons` пуст, тем нет; повтор — не дубль, пример добавлен в существующую запись один раз; род у существительного — как при быстром вводе (003), если определён (FR-012, analyze C1)
- [ ] T021 [US2] `vocab/edits.py` — тесты T020 проходят; `vocab/entry.html` — у примера мелко «урок N» (FR-012: урок виден в «Подробнее») + тест разметки
- [ ] T022 [P] [US2] Тесты `POST /vocab/from-text`: слово (форма, verb/word, род существительного), фраза, предложение (пример не дублируется), абзац → 422, без перевода → 422, повтор → `merged: true`
- [ ] T023 [US2] Маршрут `/vocab/from-text` — тесты T022 проходят
- [ ] T024 [US2] `translate.js`: «+ В словарь: X» → запрос с предложением вокруг выделения и уроком страницы → «✓ в словаре: перевод» + сообщение внизу
- [ ] T025 [US2] Проверка quickstart §2 (в т. ч. «Подробнее», оборот карточки, происхождение)

---

## Phase 5: User Story 3 + 4 — озвучка и переключатель (P2)

- [ ] T026 [P] [US4] Тесты: `POST /settings/translate` ставит cookie и возвращает назад; пункт «Перевод при выделении» в «⋯» с состоянием
- [ ] T027 [US4] Маршрут и пункт меню — тесты T026 проходят
- [ ] T028 [US3][US4] Проверка quickstart §3 и §4

---

## Phase 6: Настройки перевода

- [ ] T029 [P] Тесты: `/settings` показывает сервис, статус ключа DeepL, почту, число записей запаса; `POST /settings/translator` (DeepL без ключа — ошибка), `POST /settings/translations/clear`
- [ ] T030 Блок «Перевод» в `vocab/settings.html` и маршруты — тесты T029 проходят
- [ ] T031 Проверка quickstart §5

---

## Phase 7: Polish

- [ ] T032 Проверка quickstart §6 (начальная форма, SC-005) и §7 (тема, 375 px)
- [ ] T033 [P] ruff, весь pytest; `CLAUDE.md` проекта (пакет `translate/`, `translate.js`, ключ DeepL в `.env`); `.env.example`
- [ ] T034 Показ пользователю частями (перевод → в словарь → настройки), приёмка; CHANGELOG, ✅ в дорожной карте, слияние в main

---

## Dependencies

- Phase 2 → всё; T017 (зоны подсказки) → T018, T024.
- US2 зависит от US1 (перевод в подсказке и `/translate`).
- US3/US4 и настройки — после US1, параллельно друг другу.

## MVP

Phase 1–3: перевод выделенного с формой и 🔊 везде, где есть французский.
