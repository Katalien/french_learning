---

description: "Задачи реализации функции 003 — словарь и карточки"
---

# Tasks: Словарь и карточки

**Input**: `specs/003-vocabulary-flashcards/` — plan.md, spec.md, research.md, data-model.md,
contracts/ui-routes.md, quickstart.md

**Tests**: ОБЯЗАТЕЛЬНЫ (конституция XIII, TDD); интерфейс — вручную по quickstart.md.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Добавить зависимость `fsrs` в `pyproject.toml` (`uv add fsrs`), закрепить версию в `uv.lock` (research R2)
- [X] T002 [P] Дополнить формат: необязательные поля `hidden: bool` и `completed_by_ai: list[str]` у лексики — тесты в `tests/unit/test_schema.py`, модель в `src/french_learning/content/schema.py`, описание в `docs/content-format.md`
- [X] T003 [P] В `init-content` и для существующего хранилища: `.progress/` в `.gitignore` хранилища (`src/french_learning/agent/storage.py` + функция `ensure_progress_ignored`, вызывается при открытии БД прогресса); тест в `tests/unit/agent/test_storage.py`

---

## Phase 2: Foundational

### База прогресса (TDD)

- [X] T004 [P] Тесты в `tests/unit/practice/test_db.py`: БД создаётся в `CONTENT_DIR/.progress/progress.sqlite` со схемой data-model (`meta`, `settings`, `cards`, `reviews`, `sessions`), `schema_version` = 1; повторное открытие не теряет данных; настройки по умолчанию `portion_size=20`, `directions=staged`
- [X] T005 Реализовать `src/french_learning/practice/db.py` (стандартный `sqlite3`, миграции по `schema_version`) — тесты T004 проходят

### Проверка ответа (TDD, общая с 004)

- [X] T006 [P] Тесты в `tests/unit/practice/test_checking.py`: апострофы `'` `’` `ʼ`, регистр, лишние и неразрывные пробелы, пробел перед `?` `!` `;` `:`, конечная точка — не ошибка; буква или диакритика — ошибка (`été` ≠ `ete` → результат «нужен выбор написания»); несколько допустимых ответов; варианты написания: правильный + до 3 подмен акцентов на тех же буквах (e ↔ é è ê ë, a ↔ à â, u ↔ ù û ü, i ↔ î ï, o ↔ ô, c ↔ ç, oe ↔ œ), без повторов, правильный среди них; русский ответ — без учёта регистра, «ё» = «е»
- [X] T007 Реализовать `src/french_learning/practice/checking.py` — тесты T006 проходят

### Карточки и расписание (TDD)

- [X] T008 [P] Тесты в `tests/unit/vocab/test_cards.py`: синхронизация создаёт карточку `fr_ru` для каждой нескрытой записи; `ru_fr` — после первой «Помню» в `fr_ru` при `staged`, сразу при `both`; оценки again / hard / good меняют `due` через FSRS (good → позже, чем again); направления независимы (SC-002); оценка в любом режиме обновляет расписание, повтор раньше срока не «ломает» интервал — слово с «Помню» через урок не появляется завтра в «пора сегодня» (SC-002a); «Знаю» приостанавливает обе карточки, возврат — снимает, история цела (SC-005); «сложные» по последним 5 оценкам (research R10); каждая оценка пишется в `reviews` с `prev_fsrs`
- [X] T009 Реализовать `src/french_learning/vocab/cards.py` (обёртка над `fsrs`) — тесты T008 проходят

### Вопрос и ответ карточки (TDD)

- [X] T010 [P] Тесты в `tests/unit/vocab/test_entries.py`: FR → RU — вопрос «la maison» / «l'eau» / «parler», ответ — все переводы; RU → FR — вопрос переводы + подсказка (часть речи, первый пример), ответ с артиклем у существительных; неопределённый артикль выводится из рода и признаков (un / une / des; `plural_only` → des; `both` → un / une); для RU → FR допустимы все записи с тем же переводом (spec, Edge Cases); фильтры словаря: все / урок / тема / вид / known / hidden / incomplete
- [X] T011 Реализовать `src/french_learning/vocab/entries.py` — тесты T010 проходят

**Checkpoint**: карточки, расписание и проверка работают без интерфейса

---

## Phase 3: User Story 1 — Повторить карточки (P1) 🎯 MVP

### Tests ⚠️

- [X] T012 [P] [US1] Тесты в `tests/unit/vocab/test_sessions.py`: сеанс из словаря — порции по N из настроек, после порции итог и «продолжить / закончить»; из урока — все карточки урока одной очередью; режимы today / lesson / topic / all / hard и вид word / verb / phrase / all; направление; «пора сегодня» включает новые без ограничения и показывает число до начала; нет карточек → сообщение; закрытие посреди сеанса — оценки сохранены (FR-035c); «Отменить» — только последняя оценка текущего сеанса: состояние карточки восстановлено, запись оценки удалена, позиция −1
- [X] T013 [P] [US1] Интеграционные тесты в `tests/integration/test_vocab_practice.py`: `GET /practice` → `POST /practice/start` → карточка без ответа → `show` → ответ и кнопки оценок (оценки до показа недоступны) → `rate` → следующая карточка; `undo`; `GET /lessons/14/practice`-аналог на образце (`/lessons/1/practice`) запускает все слова урока

### Implementation

- [X] T014 [US1] Реализовать `src/french_learning/vocab/sessions.py` — тесты T012 проходят
- [X] T015 [US1] Маршруты повторения в `src/french_learning/web/routes/vocab.py` и шаблоны `templates/vocab/practice_setup.html`, `practice_card.html`, `practice_summary.html`; кнопка «Повторить лексику урока» в `templates/theory.html` — тесты T013 проходят
- [X] T016 [US1] Резервная копия прогресса (FR-053, FR-053a): тесты в `tests/unit/practice/test_backup.py` (дамп в `backups/progress.sql`, восстановление из дампа без потерь (SC-006), ежедневный запуск — один раз в день, коммит + отправка в фоне, без сети — дата последней успешной отправки не меняется, работа не блокируется) → реализация `src/french_learning/practice/backup.py`, `POST /backup`, запуск при первом запросе дня, команда `french-learning restore-progress`

**Checkpoint**: повторение работает на словах уроков 13 и 14 — показ пользователю

---

## Phase 4: User Story 2 — Просмотреть словарь и карточку (P2)

- [X] T017 [P] [US2] Интеграционные тесты в `tests/integration/test_vocab_pages.py`: `/vocab` с фильтрами (урок, тема, вид) и видами «карточки / список»; карточка: род — класс цвета и метка `m` / `f`, у записей без рода — нейтральный; доп. блок свёрнут и содержит формы, спряжение, заметки, уроки, пример; кнопка 🔊 с текстом записи
- [X] T018 [US2] Шаблоны `templates/vocab/list.html`, `entry.html`, `partials/entry_card.html`; `static/js/speech.js` (speechSynthesis fr-FR, сообщение при недоступности); стили рода в `app.css`; пункт меню «Словарь» — тесты T017 проходят

---

## Phase 5: User Story 3 — Добавить свои слова (P3)

- [X] T019 [P] [US3] Тесты в `tests/unit/vocab/test_parsing.py`: разделители « — » « – » « - » и табуляция; переводы через `,` `;`; артикли le / la / l' / les; пометки `(m)` `(f)` `(v)` `(adj)` `(phr)`; `?` / `!` / многословное без артикля → фраза; пустые строки и `#` пропускаются; несколько тире — разбор по первому, при сомнении — строка «не распознана»; неуказанное → `needs_completion`; реалистичный список из 50 строк мягкого формата распознаётся без правки не меньше чем на 95% (SC-003)
- [X] T020 [P] [US3] Тесты в `tests/unit/vocab/test_edits.py`: добавление одного слова (текст + хотя бы один перевод, остальное необязательно, `origin: user`); импорт списка — новые записи, объединение с существующими по форме + части речи + роду (новый перевод добавляется), отчёт «добавлено / объединено / не распознано»; один коммит на операцию
- [X] T021 [US3] Реализовать `src/french_learning/vocab/parsing.py` и `src/french_learning/vocab/edits.py` — тесты T019, T020 проходят
- [X] T022 [US3] Страницы `/vocab/add`, `/vocab/import`, `/vocab/complete` (число «нужно дополнить» + команда) и шаблоны; интеграционный тест в `tests/integration/test_vocab_add.py`
- [X] T023 [US3] Навык `.claude/skills/complete-words/SKILL.md`: записи `needs_completion: true` → заполнить род / артикль / формы / часть речи, у глаголов — группу и спряжение в настоящем времени; `completed_by_ai`; сомнения → `needs_review`; через черновик и `commit-staging`; отчёт (research R8)

---

## Phase 6: User Story 4 — Ввод ответа без французской клавиатуры (P4)

- [ ] T024 [P] [US4] Интеграционные тесты в `tests/integration/test_vocab_input.py`: переключатель «ввод ответа»; панель символов (é è ê ë à â ç œ ù û ü î ï ô) в разметке; `answer`: верный → «Помню», неверный → «Не помню» и правильный ответ; `ete` для «été» → фрагмент выбора написания; неверный выбор → ошибка; RU → FR без артикля у существительного → ошибка; любой из допустимых ответов засчитан
- [ ] T025 [US4] Реализовать ввод в `web/routes/vocab.py` и шаблоны `templates/vocab/partials/answer_input.html`, `partials/spelling_choice.html`, `partials/symbol_panel.html` (вставка в позицию курсора — Alpine.js) — тесты T024 проходят

---

## Phase 7: User Story 5 — Управлять записями (P5)

- [ ] T026 [P] [US5] Тесты в `tests/unit/vocab/test_edits.py` и `tests/integration/test_vocab_manage.py`: правка полей и заметок (`origin` изменённых полей — `user`); удаление только своих (`origin: user`) с подтверждением; записи из уроков — только скрыть (`hidden`), скрытая запись видна в лексике урока с пометкой; «Знаю» / «Вернуть»; история оценок после правки / скрытия / «Знаю» / возврата сохранена
- [ ] T027 [US5] Реализовать действия `/vocab/{id}/edit|hide|unhide|delete|known|unknown` и формы — тесты T026 проходят

---

## Phase 8: Polish

- [ ] T028 [P] Страница настроек `/settings` (размер порции, режим направлений) + тест
- [ ] T029 [P] Проверка всех новых страниц на 375 px (SC-007)
- [ ] T030 [P] `CLAUDE.md` (навык `/complete-words`, команда `restore-progress`), `README.md`, `CHANGELOG.md`, `docs/content-format.md`
- [ ] T031 Полный прогон: `ruff`, `check_no_content.py`, `pytest`
- [ ] T032 Приёмка по quickstart.md с пользователем на словах уроков 13 и 14
- [ ] T033 После приёмки: статус 003 → ✅ в `docs/roadmap.md`, слияние в `main`, отправка

---

## Dependencies & Execution Order

Setup → Foundational (T004–T011) → US1 (MVP, с резервной копией) → US2 → US3 → US4 → US5 →
Polish. US2–US5 зависят от Foundational; US4 использует `checking.py` (T007).

## Implementation Strategy

MVP = Setup + Foundational + US1: повторение настоящих слов уроков 13 и 14 и резервная копия
прогресса → показ пользователю → остальные истории.
