---

description: "Task list for 011 — повторение и лексика урока"
---

# Tasks: Повторение и лексика урока

**Input**: `/specs/011-practice-and-lesson-vocab/` (plan, spec, research, data-model, contracts, quickstart)

**Tests**: обязательны (конституция XIII) — тест пишется и падает до кода.

## Phase 1: Setup

- [X] T001 Ветка `011-practice-and-lesson-vocab`, `.specify/feature.json`, `uv run pytest` зелёный

## Phase 2: Foundational

- [X] T002 Тест в tests/unit/practice/test_db.py: схема v5 — таблица `trainer_priority` (`trainer_id`, `key`, `review_id`, `created_at`, уникальный `(trainer_id, key)`); база v4 открывается и получает таблицу без потери данных
- [X] T003 src/french_learning/practice/db.py: `SCHEMA_VERSION = 5`, таблица `trainer_priority`

## Phase 3: US1 — «Ошибка в артикле» (P1) 🎯

- [X] T004 [P] [US1] Тесты в tests/unit/vocab/test_cards.py: `rate(..., "article")` → расписание как `good`, в `reviews.rating` — `article`; `hard_ids` не считает `article` ошибкой; `undo` оценки `article` удаляет строки `trainer_priority` с её `review_id`
- [X] T005 [P] [US1] Тесты в tests/unit/trainers/test_schedule.py: ключи из `trainer_priority` — первыми в `select` (раньше добавленные — раньше); ответ на ключ снимает его приоритет
- [X] T006 [P] [US1] Тесты в tests/integration/test_vocab_practice.py: кнопка «Ошибка в артикле» есть у ru_fr существительного с родом и нет в fr_ru / у глагола; `POST rate=article` там, где кнопки нет, → 404; после оценки тренажёр «Артикли» начинается с этого слова (оба вопроса); итог — «Ошибка в артикле: 1»
- [X] T007 [US1] src/french_learning/vocab/cards.py: `RATINGS["article"] = Good`; `rate` для `article` добавляет приоритет `articles:<id>:def/indef`; `hard_ids`; `undo` снимает приоритет
- [X] T008 [US1] src/french_learning/trainers/schedule.py: приоритет в `select`; снятие в `answer`
- [X] T009 [US1] src/french_learning/web/routes/vocab.py и templates/vocab/practice_card.html, practice_summary.html: условие кнопки (`vocab_entries.article_rating_allowed`), проверка в `practice_rate`, строка в итоге; стиль кнопки в static/css/screens.css

## Phase 4: US2 — переводы помещаются (P1)

- [X] T010 [P] [US2] Тесты в tests/integration/test_vocab_practice.py: ru_fr лицевая и fr_ru обратная сторона — переводы отдельными `.tr-line`; длинные — класс `tr-m` / `tr-s`; страница результата ввода — так же
- [X] T011 [US2] src/french_learning/vocab/entries.py: `Question.lines`; фильтр/функция класса размера по длине
- [X] T012 [US2] templates/vocab/practice_card.html, practice_result.html; static/css/screens.css: `.tr-line`, `.tr-m`, `.tr-s`, `overflow-wrap: anywhere`

## Phase 5: US3 — повтор-тренировка (P2)

- [X] T013 [P] [US3] Тесты в tests/unit/vocab/test_sessions.py: `drill_candidates(session, which)` — по последней оценке слова в сеансе; `start_drill` — очередь из них; `rate` в тренировке не меняет `cards` и `reviews`; `summary` и `undo` тренировки — из состояния сеанса
- [X] T014 [P] [US3] Тесты в tests/integration/test_vocab_practice.py: итог — кнопки с числами только при N > 0; `POST /practice/{id}/drill` → новый сеанс; пометка «Тренировка — без записи»; итог тренировки предлагает повтор по её ответам; «article» в повтор не входит
- [X] T015 [US3] src/french_learning/vocab/sessions.py: `SessionParams.drill`, `drill_candidates`, `start_drill`, ветки в `rate` / `undo` / `summary`
- [X] T016 [US3] src/french_learning/web/routes/vocab.py: маршрут `drill`, контекст итога; templates/vocab/practice_summary.html и practice_card.html (пометка)

## Phase 6: US4 — фильтры лексики урока (P2)

- [X] T017 [P] [US4] Тесты в tests/integration/test_vocab_pages.py: `/lessons/n/vocab?topic=&kind=` — фильтры (темы только слов урока), суженные списки, «Нет слов для выбранных условий»; ссылки несут фильтр; страница слова — «N из M» и соседи по фильтру; «назад» с фильтром
- [X] T018 [US4] src/french_learning/web/routes/lessons.py (лексика урока): фильтры; templates/lesson_vocab.html, partials/vocab_list.html
- [X] T019 [US4] src/french_learning/web/routes/vocab.py `_source_list`: фильтры `topic` / `kind` для `from=lesson`

## Phase 7: US5 — темы со словами (P3)

- [X] T020 [P] [US5] Тест в tests/integration/test_vocab_practice.py: тема без слов отсутствует в списке настройки; `?mode=topic&topic=<пустая>` — не выбрана, счётчик 0
- [X] T021 [US5] src/french_learning/web/routes/vocab.py `practice_setup`: `topic_options` только с темами слов

## Phase 8: Polish

- [X] T022 `uv run pytest`, `ruff check`, `ruff format`, `check_no_content.py`
- [X] T023 Проверка на демо по quickstart.md (1280 и 375 px), скриншоты
- [X] T024 [P] CHANGELOG.md — 0.10.0 «на приёмке»; docs/roadmap.md; CLAUDE.md (кратко про 011)
- [ ] T025 После «принимаю»: `main`, GitHub, `update-app.ps1`; roadmap 011 ✅

## Dependencies

Phase 2 → US1 (таблица). US2–US5 независимы от US1 и друг от друга; общие файлы
(`vocab.py`, `practice_card.html`, `practice_summary.html`, `screens.css`) правятся по очереди.
**MVP**: US1 + US2.
