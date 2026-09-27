---

description: "Задачи реализации функции 004 — упражнения с автопроверкой и тренажёры"
---

# Tasks: Упражнения с автопроверкой и тренажёры

**Input**: `specs/004-exercises-trainers/` — plan.md, spec.md, research.md, data-model.md,
contracts/ (ui-routes, cli, trainers-format), quickstart.md

**Tests**: ОБЯЗАТЕЛЬНЫ (конституция XIII, TDD); интерфейс — интеграционные тесты маршрутов
и вручную по quickstart.md.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Образец для тестов: в `tests/fixtures/content` — упражнения всех типов с несколькими допустимыми ответами, ответом с `l'`, ответом с диакритикой (`été`), пунктом с `needs_review`; словарь — существительные m / f / both / `plural_only` / `h_aspire` / на гласную, 2 глагола со спряжением в présent, 2 прилагательных с формами; `trainers.yaml` с одним тренажёром `negation` (agent) и пакет `trainers/negation/tb-*.yaml` на 5 заданий
- [ ] T002 [P] Пакеты `src/french_learning/exercises/` и `src/french_learning/trainers/` (с `generators/`), папки тестов `tests/unit/exercises/`, `tests/unit/trainers/`

---

## Phase 2: Foundational

### Формат (TDD)

- [ ] T003 [P] Тесты в `tests/unit/test_schema.py` и `tests/unit/test_loader.py`: префикс `tb`; модель `TaskBatch` (тип из поддерживаемых, пункты по моделям 001, `new_words` ≤ 2 с переводом); `TrainerEntry` (slug, для встроенного id — только `source` и `rules`); загрузка `trainers.yaml` и `trainers/*/tb-*.yaml`; пакет для тренажёра не из каталога или с чужим типом — ошибка загрузки без падения остального; хранилище без этих файлов корректно
- [ ] T004 Реализовать в `src/french_learning/content/schema.py`, `loader.py`, `index.py` (доступ к каталогу и пакетам), `agent/ids.py` (`tb`) — тесты T003 проходят; описать формат в `docs/content-format.md`

### База прогресса v2 (TDD)

- [ ] T005 [P] Тесты в `tests/unit/practice/test_db.py`: миграция v1 → v2 добавляет `exercise_attempts`, `trainer_cards`, `trainer_answers`, `trainer_sessions`, данные v1 целы; `schema_version` = 2; настройка `trainer_portion_size` = 20; дамп резервной копии включает новые таблицы
- [ ] T006 Реализовать миграцию в `src/french_learning/practice/db.py` — тесты T005 проходят

### Проверка ответов по типам (TDD)

- [ ] T007 [P] Тесты в `tests/unit/exercises/test_grading.py`: для каждого типа (`gap_choice`, `gap_input`, `multi_gap`, `transform`, `true_false`, `choice` с одним и несколькими ответами, `two_forms`, `grouping`, `picture` с ответами; `picture` без ответов — как открытый ответ) — верно / неверно по пропускам и пункту целиком; `de l’` и `De l'` = `de l'`; пробел перед `?` и точка в трансформации; любой из допустимых ответов; `ete` → `choose` с вариантами; пустой ответ — неверно; `open` — без проверки (SC-002)
- [ ] T008 Реализовать `src/french_learning/exercises/grading.py` (на основе `practice/checking.py`) — тесты T007 проходят

**Checkpoint**: формат, база и проверка готовы — можно делать истории.

---

## Phase 3: User Story 1 — выполнить упражнение и проверить себя (P1) 🎯 MVP

**Goal**: упражнение урока решается в интерфейсе, проверяется целиком, ошибки исправляются,
ответ открывается; счётчик домашки работает.

**Independent Test**: quickstart, сценарии 1–3.

- [ ] T009 [P] [US1] Тесты в `tests/unit/exercises/test_attempts.py`: черновик сохраняется и читается; первая проверка фиксирует `first_results`; исправление после подсветки → `fixed_self`; «Показать ответ» → `revealed` и итог `wrong`; выбор написания откладывает итог пункта до выбора, неверный выбор → `wrong`; открытый ответ → `saved`; `is_done` — после первой полной проверки независимо от результата (FR-022)
- [ ] T010 [US1] Реализовать `src/french_learning/exercises/attempts.py` и `ExerciseProgress` (протокол в `content/progress.py`), подключить в `web/app.py` вместо `NoProgress` — тесты T009 проходят
- [ ] T011 [P] [US1] Интеграционные тесты `tests/integration/test_exercise_solve.py`: форма по каждому типу (выпадающие списки из `options`, поля, радиокнопки, чекбоксы для нескольких ответов, группы); справка скрыта за кнопкой; панель символов; `POST /exercises/{id}/draft`, `/check` (подсветка, «Показать ответ», выбор написания, пометка «требует проверки» у пункта), `/reveal/{item}`, `/save` для открытого ответа; счётчик «X из Y» на странице урока растёт после проверки
- [ ] T012 [US1] Вынести панель французских символов в `src/french_learning/web/static/js/symbols.js` (вставка в поле с фокусом) и использовать в 003 и 004
- [ ] T013 [US1] Реализовать `src/french_learning/web/routes/exercises.py` и шаблоны `web/templates/exercises/{solve,_items,_result}.html` (HTMX для проверки, Alpine для черновика и справки), форма на странице `/elements/{ex-id}` — тесты T011 проходят
- [ ] T014 [US1] Проверка страниц на ширине 375 px (SC-008): правка `static/css/app.css`

**Checkpoint**: MVP — упражнения уроков 13 и 14 решаются в приложении.

---

## Phase 4: User Story 2 — перерешать и видеть историю (P2)

**Goal**: «Решить заново», история попыток, «Мои ошибки».

**Independent Test**: quickstart, сценарии 4–5.

- [ ] T015 [P] [US2] Тесты в `tests/unit/exercises/test_attempts.py` и `tests/unit/exercises/test_mistakes.py`: «Решить заново» — новая пустая попытка, старые целы; история по датам; пересчёт при изменённом правильном ответе — пометка «пересчитано», сохранённые ответы и итоги не меняются (FR-031, SC-004); «Мои ошибки» — пункты с `wrong` в последней попытке, фильтры урок и тема, прорешанный верно пункт (`scope=item`) уходит из списка
- [ ] T016 [US2] Реализовать пересчёт в `exercises/attempts.py` и `src/french_learning/exercises/mistakes.py` — тесты T015 проходят
- [ ] T017 [P] [US2] Интеграционные тесты `tests/integration/test_exercise_history.py`: `/exercises/{id}/restart`, `/history`, `/mistakes?lesson=`, прорешивание пункта `/mistakes/{id}/{item}`
- [ ] T018 [US2] Маршруты и шаблоны `exercises/history.html`, `exercises/mistakes.html`, ссылка «Мои ошибки» в навигации — тесты T017 проходят

---

## Phase 5: User Story 4 — встроенные тренажёры (P2)

**Goal**: 9 встроенных тренажёров из словаря, чисел и уроков с FSRS по вопросам.

**Independent Test**: quickstart, сценарий 7.

### Каталог, расписание, сеансы (TDD)

- [ ] T019 [P] [US4] Тесты `tests/unit/trainers/test_catalog.py`: 9 встроенных тренажёров; `trainers.yaml` добавляет свои и переопределяет `source` / `rules` встроенных (FR-060, FR-062)
- [ ] T020 [US4] Реализовать `src/french_learning/trainers/catalog.py` и `questions.py` — тесты T019 проходят
- [ ] T021 [P] [US4] Тесты `tests/unit/trainers/test_schedule.py` и `test_sessions.py`: верно → `good`, неверно или подсмотрено → `again`; ошибочный вопрос возвращается раньше верного (SC-006); порция N = `trainer_portion_size`, сначала «пора», затем новые; набор данных: весь словарь / урок / тема / «сложные»; итог порции «X из N», «Продолжить»; ответы пишутся в `trainer_answers` сразу
- [ ] T022 [US4] Реализовать `src/french_learning/trainers/schedule.py` и `sessions.py` — тесты T021 проходят

### Генераторы (TDD; каждый — отдельная пара тест + код, [P] между собой)

- [ ] T023 [P] [US4] Артикли — `tests/unit/trainers/test_articles.py` + `trainers/generators/articles.py`: контрольный набор SC-005 (элизия, h немое, h придыхательное `héros` → `le`, оба рода `élève`, `plural_only` → `les` / `des`), два ключа на слово, ответ кнопками и вводом (FR-042–FR-044)
- [ ] T024 [P] [US4] Спряжение — `test_conjugation.py` + `generators/conjugation.py`: présent из `verb.conjugation`, время в ключе (FR-045)
- [ ] T025 [P] [US4] Женский род и множественное число — `test_forms.py` + `generators/forms.py`
- [ ] T026 [P] [US4] Притяжательные и указательные — `test_determiners.py` + `generators/determiners.py`: `mon amie`, `cet homme`, `ce héros`, `ces gens`
- [ ] T027 [P] [US4] Согласование прилагательного — `test_agreement.py` + `generators/agreement.py`
- [ ] T028 [P] [US4] Числа — `tests/unit/trainers/test_french_numbers.py` + `trainers/french_numbers.py` и `generators/numbers.py`: 0–1000, `quatre-vingt-dix-sept`, `vingt et un` и `vingt-et-un` оба верны, `quatre-vingts`, `deux cents`, `mille`
- [ ] T029 [P] [US4] «Собери предложение» — `test_sentences.py` + `generators/sentences.py`: предложения из пунктов упражнений с подставленными ответами и из текстов уроков, 4–12 слов, допустимые порядки — варианты ответов (у текстов — исходный порядок)
- [ ] T030 [US4] «Не хватает данных» для каждого генератора с подсказкой (FR-046) — тесты в `test_catalog.py`

### Интерфейс

- [ ] T031 [P] [US4] Интеграционные тесты `tests/integration/test_trainers_builtin.py`: `/trainers`, `/trainers/{id}` (выбор набора), `start`, задание (кнопки / ввод / сборка), `answer`, `spelling`, `reveal`, итог порции, `continue`; настройка размера порции
- [ ] T032 [US4] Маршруты `src/french_learning/web/routes/trainers.py`, шаблоны `web/templates/trainers/*.html` (сборка предложения — Alpine), вкладка «Тренажёры» в навигации, настройка в `/settings` — тесты T031 проходят

---

## Phase 6: User Story 3 — «Не согласна» и статус (P3)

**Goal**: сообщение об ошибке из пункта; смена статуса упражнения.

**Independent Test**: quickstart, сценарий 6.

- [ ] T033 [P] [US3] Тесты: `tests/unit/test_writer.py` — `set_exercise_status` меняет YAML, коммит; `tests/integration/test_exercise_report_status.py` — «Не согласна» создаёт сообщение с пунктом, напоминание, происхождение ответа видно при выключенном переключателе; смена статуса пересчитывает счётчики урока и переносит упражнение в список
- [ ] T034 [US3] Реализовать `ContentWriter.set_exercise_status`, маршруты `/exercises/{id}/status` и `/exercises/{id}/items/{item}/report`, формы — тесты T033 проходят

---

## Phase 7: User Story 5 — задания от агента (P3)

**Goal**: пул, архив, «Ошибки», статистика; команды и навыки для генерации и разбора.

**Independent Test**: quickstart, сценарии 8–9.

- [ ] T035 [P] [US5] Тесты `tests/unit/trainers/test_pools.py`: пул = задания минус верно решённые; неверное остаётся и попадает в «Ошибки»; пустой пул; статистика (доля верных, по дням, типичные ошибки; подсмотрено = ошибка); FSRS не ведётся
- [ ] T036 [US5] Реализовать `src/french_learning/trainers/pools.py`, сеансы для пакетов в `sessions.py` — тесты T035 проходят
- [ ] T037 [P] [US5] Интеграционные тесты `tests/integration/test_trainers_pool.py`: решение заданий пакета (подсказки `new_words` видны), «в пуле N», `/trainers/{id}/mistakes`, `/stats`, пустой пул с командой агента, «Не согласна» у задания пакета (`tb-…` в сообщении)
- [ ] T038 [US5] Маршруты и шаблоны пула, ошибок, статистики — тесты T037 проходят
- [ ] T039 [P] [US5] Тесты `tests/integration/test_agent_cli.py`: `trainers-list`, `trainer-context <id>` (правила, словарь, темы пройденных уроков, существующие задания), `mistakes-list --trainer / --lesson`; пакет через черновик проходит `stage-check` и `commit-staging`
- [ ] T040 [US5] Реализовать команды в `src/french_learning/agent/commands.py`, описать в `specs/004-exercises-trainers/contracts/cli.md` — тесты T039 проходят
- [ ] T041 [US5] Навыки `.claude/skills/generate-tasks/SKILL.md` и `.claude/skills/explain-mistakes/SKILL.md` (правила: лексика словаря и пройденных уроков, ≤ 2 новых слов с переводом, `origin: ai`, `needs_review` при сомнениях, только по просьбе)

---

## Phase 8: User Story 6 — свой тренажёр (P4)

**Goal**: агент добавляет тренажёр в каталог без изменения кода.

**Independent Test**: quickstart, сценарий 8 (начало).

- [ ] T042 [P] [US6] Тест: запись в `trainers.yaml` с существующим типом → тренажёр во вкладке и в `trainers-list` без изменения кода (SC-007); переопределение встроенного `source: agent` → задания из пула
- [ ] T043 [US6] Навык `.claude/skills/add-trainer/SKILL.md` (запись через черновик; новый тип — сообщить о доработке, не добавлять)

---

## Phase 9: Polish

- [ ] T044 [P] Все новые страницы на 375 px (SC-008), доступность форм (подписи полей)
- [ ] T045 [P] `CLAUDE.md` (навыки, команды), `README.md`, `CHANGELOG.md`, `docs/content-format.md`, `docs/roadmap.md`
- [ ] T046 Полный прогон: `ruff`, `check_no_content.py`, `pytest`
- [ ] T047 Приёмка по quickstart.md с пользователем на уроках 13 и 14, включая замер качества SC-005 из 002
- [ ] T048 После приёмки: статус 004 → ✅, релиз в CHANGELOG, слияние в `main`, отправка

---

## Dependencies & Execution Order

Setup → Foundational (T003–T008) → US1 (MVP) → US2 → US4 → US3 → US5 → US6 → Polish.
US2 и US3 зависят от US1 (попытки, страница упражнения). US4 зависит только от
Foundational и может идти параллельно с US2. US5 использует сеансы US4 (T022) и формат
пакетов (T004). US6 — от US5.

## Parallel Opportunities

- T003, T005, T007 — независимые тесты фундамента.
- Генераторы T023–T029 — отдельные файлы, делаются в любом порядке.
- Интеграционные тесты каждой истории пишутся параллельно с модульными.

## Implementation Strategy

MVP = Setup + Foundational + US1: домашка уроков 13 и 14 решается и проверяется в приложении.
Показ пользователю → US2 → US4 (встроенные тренажёры) → показ → US3 → US5 → US6 → приёмка.
