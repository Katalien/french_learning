---

description: "Task list for 010 — правки после первого использования"
---

# Tasks: Правки после первого использования

**Input**: Design documents from `/specs/010-first-use-fixes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-routes.md, quickstart.md

**Tests**: обязательны — конституция XIII (TDD): тест пишется и падает до кода.

**Organization**: по пользовательским историям spec.md. Пункт 8 (скорость) и отказ от
поэтапного режима — фундамент (Phase 2): от них зависят сеансы US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно параллельно (разные файлы, нет зависимостей)
- **[Story]**: US1–US6 из spec.md

## Phase 1: Setup

- [X] T001 Убедиться, что ветка `010-first-use-fixes`, `uv run pytest` зелёный до правок; `.specify/feature.json` → `specs/010-first-use-fixes`

---

## Phase 2: Foundational — скорость (пункт 8) и обе стороны

**Purpose**: карточки заводятся только недостающие и сразу в обоих направлениях (research R1, R2)

- [X] T002 Тест в tests/unit/vocab/test_cards.py: `sync` создаёт карточки `fr_ru` и `ru_fr` для каждого нескрытого слова независимо от настройки `directions`; повторный `sync` не создаёт ни одного `fsrs.Card` (подменить `fsrs.Card` счётчиком через monkeypatch); существующие карточки и их FSRS-состояние не меняются
- [X] T003 Тест в tests/unit/vocab/test_cards.py: `rate(..., "good")` по `fr_ru` больше не зависит от `staged` (ветка удалена); переписать/удалить старые тесты поэтапного режима в tests/unit/vocab/test_cards.py и tests/unit/vocab/test_sessions.py
- [X] T004 Реализовать в src/french_learning/vocab/cards.py: `sync` читает имеющиеся `(entry_id, direction)` одним запросом и вызывает `_insert` только для недостающих, всегда обе стороны; убрать ветку `staged` из `rate`
- [X] T005 Тест в tests/integration/test_settings.py: на `/settings` нет полей `directions` и `portion_size`; `POST /settings` без них работает и сохраняет прочие настройки
- [X] T006 Убрать блоки «Новые слова» и «Карточек за один подход» из src/french_learning/web/templates/vocab/settings.html и их разбор/проверку из `settings_page` / `settings_save` в src/french_learning/web/routes/vocab.py
- [X] T007 Замер: скрипт research R1 на копии хранилища в scratchpad — запрос `/practice/{id}` < 0,25 с; результат записать в research.md (R1, «после»)

**Checkpoint**: оценка карточки быстрая; у всех слов обе карточки

---

## Phase 3: User Story 1 — Повторить слова урока или темы так, как хочется (P1) 🎯 MVP

**Goal**: из урока — страница настройки; все слова отбора в любом направлении; перемешивание; «слов за подход» на странице настройки; тема с поиском (пункты 3, 5, 6, 11)

**Independent Test**: урок с 20 словами → «Повторить слова урока» → «русский → французский» → в сеансе 20 карточек; два запуска — разный порядок; ввод «прон» в поле темы фильтрует список

### Tests for User Story 1

- [X] T008 [P] [US1] Тест в tests/unit/vocab/test_sessions.py: с `random.Random(seed)` очередь режимов урок/тема/все перемешана (не равна сортировке по id) и детерминирована при одном seed; «сегодня» — сначала повторявшиеся с подошедшим сроком, затем новые, каждая группа перемешана
- [X] T009 [P] [US1] Тест в tests/unit/vocab/test_sessions.py: `SessionParams.portion=None` → один подход на всю очередь; `portion=5` → порции по 5; старый сеанс без поля `portion` в JSON читается
- [X] T010 [P] [US1] Тест в tests/integration/test_vocab_practice.py: `GET /lessons/{n}/practice` → 303 на `/practice/setup?mode=lesson&lesson={n}`; 404 для несуществующего урока; `/practice/setup?mode=lesson&lesson=n` — отмечен «По уроку» и выбран урок n, поле `portion` пусто
- [X] T011 [P] [US1] Тест в tests/integration/test_vocab_practice.py: `POST /practice/start` с `portion` пусто → все карточки в одном подходе; `portion=7` → подход 7 и `portion_size`=7 в настройках; `portion=0`/`abc` → ошибка формы; пустая очередь → возврат на настройку с «Нет слов для повторения»
- [X] T012 [P] [US1] Тест в tests/integration/test_vocab_practice.py: `GET /practice/count?mode=lesson&lesson=n&direction=ru_fr&kind=all` → число = все нескрытые слова урока без «Знаю»; при 0 — «Нет слов для повторения»
- [X] T013 [P] [US1] Тест в tests/integration/test_vocab_practice.py: страница настройки содержит поле темы-комбобокс (`data-combobox`, скрытое `name="topic"`, JSON списка тем) и не содержит `<select name="topic">`

### Implementation for User Story 1

- [X] T014 [US1] src/french_learning/vocab/sessions.py: поле `portion: int | None = None` в `SessionParams`; генератор `rng` в `SessionStore.__init__` (по умолчанию `random.Random()`); перемешивание в `queue` по research R3; `start` берёт размер подхода из `params.portion` (None → длина очереди)
- [X] T015 [US1] src/french_learning/web/app.py (строка `SessionStore(app.state.progress_db, app.state.cards)`): генератор по умолчанию — `random.Random()`; тесты подменяют `app.state.sessions.rng`
- [X] T016 [US1] src/french_learning/web/routes/vocab.py: `practice_setup` принимает `mode, lesson, topic`, отдаёт `portion_size`; `lesson_practice` → 303 на настройку; `practice_start` принимает и проверяет `portion` (пусто | 1–500), сохраняет `portion_size`, пустая очередь → 303 на `/practice/setup?...&notice=Нет слов для повторения`; новый `GET /practice/count` (фрагмент)
- [X] T017 [P] [US1] Новый частичный шаблон src/french_learning/web/templates/partials/combobox.html: Alpine-поле с выпадающим списком, фильтр «подстрока без регистра и акцентов» (NFD), стрелки/Enter/Escape, «Ничего не найдено», скрытое поле значения (research R5)
- [X] T018 [US1] src/french_learning/web/templates/vocab/practice_setup.html: начальные значения из запроса, комбобокс темы, поле «Слов за подход» (placeholder «все»; Alpine: урок/тема → пусто, иначе `portion_size`), блок `#practice-count` с `hx-get="/practice/count"` по `change` формы, «Начать» неактивна при 0 или без темы в режиме «по теме»; вывод `notice`
- [X] T019 [P] [US1] Стили комбобокса и счётчика в src/french_learning/web/static/css/screens.css (без `.gap`, `.chips`)
- [X] T020 [US1] Подпись кнопки в src/french_learning/web/templates/lesson_vocab.html остаётся «Повторить слова урока»; проверить прочие ссылки на `/lessons/{n}/practice` (grep по templates)

**Checkpoint**: US1 проверяется по quickstart §2–4, §6

---

## Phase 4: User Story 2 — Карточка «русский → французский» не подсказывает род (P1)

**Goal**: лицевая сторона ru_fr без цвета и метки рода (пункт 2, research R6)

**Independent Test**: сеанс ru_fr со словом f — лицевая сторона нейтральная; после переворота — цвет и метка

- [X] T021 [P] [US2] Тест в tests/integration/test_vocab_practice.py: карточка ru_fr (самооценка) — лицевая `.flip-face` с классом `neutral` и без `.gender-tag`, обратная — `.gender-tag` с родом; режим ввода ru_fr до проверки — `gender-none`, после ответа — `gender-f`; fr_ru — без изменений
- [X] T022 [US2] src/french_learning/web/templates/vocab/practice_card.html: класс `neutral` на лицевой стороне при `direction == "ru_fr"`, метка рода на обратной стороне ru_fr; в режиме ввода класс рода только после показа/проверки
- [X] T023 [P] [US2] src/french_learning/web/static/css/screens.css: `.flip-face.neutral .stripe` — нейтральный цвет (как `gender-none`)

**Checkpoint**: quickstart §5

---

## Phase 5: User Story 3 — Листать слова словаря со страницы слова (P2)

**Goal**: стрелки «‹ ›» и «N из M» по списку с фильтрами (пункт 1, research R7)

**Independent Test**: фильтр по уроку → второе слово → «›» — третье, «‹» — первое

- [ ] T024 [P] [US3] Тест в tests/integration/test_vocab_pages.py: ссылки списка `/vocab?lesson=n` ведут на `/vocab/{id}?lesson=n…`; страница слова с параметрами — `prev`/`next` по отфильтрованному списку, «2 из M»; у первого нет активной «‹»; без параметров — по всему словарю
- [ ] T025 [US3] src/french_learning/web/routes/vocab.py `vocab_entry`: параметры `lesson, topic, kind, filter`; список через `filter_entries` (с `known_ids`), позиция, соседи, строка запроса для ссылок
- [ ] T026 [US3] src/french_learning/web/templates/vocab/entry.html: стрелки `.arrow.prev/.next` (как в element.html) с подписью-словом и «N из M»; src/french_learning/web/templates/vocab/list.html и src/french_learning/web/templates/partials/vocab_list.html — ссылки на слово с текущими фильтрами
- [ ] T027 [P] [US3] src/french_learning/web/static/css/screens.css: расположение стрелок на странице слова (если стили упражнения не подходят)

**Checkpoint**: quickstart §7

---

## Phase 6: User Story 4 — Удобное решение упражнения (P2)

**Goal**: панель букв под полем, «рядом» по умолчанию без дублирующих ссылок, картинка у всех (пункты 4, 9, 10)

**Independent Test**: quickstart §8–10

- [ ] T028 [P] [US4] Тест в tests/integration/test_exercise_layout.py: в упражнении с вводом одна `.symbol-panel` с атрибутом `hidden` и `data-floating`; нет текстов «Теория к упражнению» / «Текст к упражнению»; есть кнопки «Теория рядом» / «Текст рядом» и ссылка «Открыть отдельной страницей» в панели; атрибут автозапуска «рядом» указывает на текст, если он есть, иначе на теорию
- [ ] T029 [P] [US4] Тест в tests/integration/test_exercise_layout.py: упражнение `show_source: false` с картинкой-источником — блок `.exercise-source` и кнопка «Показать картинку», начальное состояние свёрнуто; `type: picture` — открыто; источник docx/pdf или без файла — блока нет
- [ ] T030 [US4] src/french_learning/web/templates/exercises/solve.html: убрать ссылки `📖`/`📘`; панель букв `hidden data-floating`; блок картинки при файле-картинке, `x-data` `picture: {{ show_source }}`, `:class` сетки `with-source` только при открытой картинке (research R10)
- [ ] T031 [US4] src/french_learning/web/static/js/symbols.js: перенос панели `[data-floating]` в конец `li` поля при `focusin`, скрытие при уходе фокуса из полей формы; поведение вставки символа не меняется; после HTMX-замены формы — работает (делегирование событий)
- [ ] T032 [US4] src/french_learning/web/static/css/screens.css: убрать `position: sticky` у `.solve-form .symbol-panel`; стиль панели под полем
- [ ] T033 [US4] src/french_learning/web/templates/element.html: автозапуск «рядом» на ≥ 900 px (`x-init` + `matchMedia`, текст → иначе теория), ссылка «Открыть отдельной страницей» (`:href="'/elements/' + shown"`) в `.side-pane-bar`

**Checkpoint**: quickstart §8–10, §13

---

## Phase 7: User Story 5 — Видно, что сообщение отправлено (P2)

**Goal**: «Отправляю…», подтверждение и метка у пункта, без перечитывания контента (пункт 7, research R11)

**Independent Test**: quickstart §11

- [ ] T034 [P] [US5] Тест в tests/integration/test_exercise_report_status.py: отправка — ответ содержит `.report-status` внутри `#item-{n}` с текстом «Сообщение сохранено», метку «сообщение отправлено» у пункта, ответы в полях сохранены, в хранилище один `reports/*.yaml`; пустой комментарий — подсказка «Напишите, почему ответ неверный» у пункта, файлов нет; ошибка записи (`WriteError` через monkeypatch) — «Сообщение не отправлено: …» внутри `#item-{n}`
- [ ] T035 [P] [US5] Тест в tests/unit/test_writer.py: `create_report(..., known_element=True)` не вызывает `load_content` (monkeypatch), без флага — проверка как раньше
- [ ] T036 [US5] src/french_learning/content/writer.py: параметр `known_element: bool = False` в `create_report` — пропустить `_element` / проверку пакета
- [ ] T037 [US5] src/french_learning/web/routes/exercises.py `report_item`: пустой комментарий → подсказка у пункта; вызов с `known_element=True`; в контекст `report_notice={item_id: текст}`; `solve_context` — множество `reported_items` из открытых `index.reports()` для упражнения (+ только что отправленный пункт)
- [ ] T038 [US5] src/french_learning/web/templates/exercises/solve.html: кнопка с `hx-disabled-elt="this"` и индикатором «Отправляю…»; `.report-status` в `item-actions` пункта; метка «✉ сообщение отправлено»; стили в src/french_learning/web/static/css/screens.css

**Checkpoint**: quickstart §11

---

## Phase 8: User Story 6 — Классная работа выполнена (P3)

**Goal**: упражнения «В классе» всегда выполнены (пункт 12, research R12)

**Independent Test**: урок → «В классе» — «✓ выполнено» у всех

- [ ] T039 [P] [US6] Тест в tests/integration/test_lessons_pages.py: `/lessons/{n}/tasks?part=class` — у всех упражнений «✓ выполнено» без попыток; домашка — только проверенные; меню урока (`lesson_tree`) — классные отмечены; сводка домашки не меняется
- [ ] T040 [US6] src/french_learning/content/index.py: функция `exercise_done(e, progress)`; использовать в `lesson_tree`
- [ ] T041 [US6] src/french_learning/web/routes/lessons.py: множество `done` через `exercise_done`

**Checkpoint**: quickstart §12

---

## Phase 9: Polish & Cross-Cutting

- [ ] T042 Полный прогон `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`, `uv run python scripts/check_no_content.py`
- [ ] T043 Проверка на демо (порт 8010) по quickstart.md §1–13 в браузере, включая 375 px; скриншоты пользователю
- [ ] T044 [P] CHANGELOG.md — раздел версии 0.9.0 «на приёмке» со всеми 12 пунктами и отказом от поэтапного режима
- [ ] T045 [P] Документация: CLAUDE.md (если меняется описание), specs/003-vocabulary-flashcards/spec.md — пометка, что поэтапный режим отменён 010; docs/roadmap.md — «Текущее состояние»
- [ ] T046 После «принимаю»: влить в `main`, отправить на GitHub, `update-app.ps1`; roadmap 010 ✅

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (T002–T007) → US1 (сеансы опираются на обе стороны и быстрый `sync`).
- US2, US3, US4, US5, US6 не зависят от US1 и друг от друга; можно после Phase 2 в любом
  порядке. Общий файл `screens.css` — правки последовательно.
- В каждой истории тесты (T008–T013, T021, T024, T028–T029, T034–T035, T039) пишутся и падают
  до реализации.
- Phase 9 — после всех историй.

## Parallel Example: User Story 1

```text
T008, T009 (test_sessions.py) — последовательно в одном файле
T010–T013 (test_vocab_practice.py) — один файл, последовательно; параллельно с T008–T009
T017 (combobox.html) и T019 (CSS) — параллельно с T014–T016
```

## Implementation Strategy

- **MVP**: Phase 2 + US1 + US2 — самые частые действия (повторение слов) и скорость.
- Затем US4 и US5 (упражнения), US3 (словарь), US6 (классная работа).
- Вся функция выпускается одной версией 0.9.0 после проверки на демо и «принимаю».
