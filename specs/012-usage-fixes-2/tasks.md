# Tasks: Правки после использования — второй список (012)

**Input**: `specs/012-usage-fixes-2/` — spec, plan, research (R1–R9), data-model, contracts/ui-routes.md, quickstart
**Tests**: TDD (конституция XIII) — тест пишется до кода и сначала падает; поведение в браузере
(раскладка, клавиши, звук на слух) — проверка на демо (порт 8010).

Формат: `- [ ] T### [P?] [US?] Описание — файл`

## Phase 1: Setup

- [X] T001 Внести 012 в CHANGELOG: раздел «0.11.0 — на приёмке» со списком пунктов 1, 3–10 — `CHANGELOG.md`
- [X] T002 Пополнить демо-хранилище для проверок: у урока 1 есть и классные, и домашние упражнения; одно скрытое слово урока; тема раздела «Лексика» без слов (только упражнение); слова у последнего урока — демо в `.claude/launch.json` (`french-learning-demo`, вне репозитория)

## Phase 2: Foundational

- [X] T003 `ContentIndex.lesson_vocabulary` — без скрытых слов (`not e.hidden`); тест «скрытое слово не в новых и не на повторение» — `src/french_learning/content/index.py`, `tests/unit/test_index.py`

(Нужен US1, US6, US7: все считают слова урока и темы через индекс.)

## Phase 3: US1 — Скрытые слова не мешают, лишние можно удалить (P1)

**Goal**: скрытые видны только в фильтре «скрытые»; любое слово можно удалить с подтверждением.
**Independent Test**: quickstart п. 4.

- [X] T004 [P] [US1] Тесты: лексика урока и страница темы без скрытого слова и без «скрыто»; счётчик «Лексика» панели урока его не считает; словарь с `flag=hidden` — есть — `tests/integration/test_vocab_pages.py`, `tests/integration/test_topics_pages.py`
- [X] T005 [P] [US1] Тесты: `VocabEditor.delete` удаляет слово из урока (раньше `VocabError`); POST `/vocab/{id}/delete` → 303 на `/vocab`, сообщение «Слово удалено.»; слово пропало из лексики урока и поиска; карточки FSRS слова остались в базе (VII) — `tests/unit/vocab/test_edits.py`, `tests/integration/test_vocab_manage.py`
- [X] T006 [P] [US1] Тест: незаконченный сеанс повторения со словом, которое удалили, — следующая карточка открывается без ошибки, удалённое пропущено; слово, скрытое во время сеанса, доходит до конца сеанса, а новый сеанс его не берёт — `tests/integration/test_vocab_practice.py`
- [X] T007 [US1] Слова темы без скрытых: вкладки и счётчики страницы темы (`topic_page`) и `_by_topic` для слов — `src/french_learning/content/index.py`, `src/french_learning/web/routes/topics.py`
- [X] T008 [US1] Убрать пометку «скрыто» из общих списков (`partials/vocab_list.html`; в `vocab/list.html` — оставить только при фильтре «скрытые») — `src/french_learning/web/templates/partials/vocab_list.html`, `src/french_learning/web/templates/vocab/list.html`
- [X] T009 [US1] `VocabEditor.delete` — для любого слова (убрать запрет для слов из уроков); сообщение коммита «Словарь: удалено «…»» как раньше — `src/french_learning/vocab/edits.py`
- [X] T010 [US1] Пропуск удалённых слов в сеансе повторения (если T006 падает) — `src/french_learning/vocab/sessions.py`
- [X] T011 [US1] Кнопка «Удалить слово» на странице любого слова + `<dialog>` подтверждения: «Удалить «{слово}» из словаря? Действие нельзя отменить из приложения.» — «Удалить» (POST) / «Отмена» — `src/french_learning/web/templates/vocab/entry.html`, `src/french_learning/web/static/css/components.css`
- [X] T012 [US1] Соседи для стрелок карточки слова не включают скрытые (проверить тестом соседей урока / темы) — `src/french_learning/web/routes/vocab.py`, `tests/integration/test_vocab_pages.py`

## Phase 4: US2 — Раскладка упражнения не прыгает после проверки (P1)

**Goal**: после «Проверить» / «Сбросить» / «Подсмотреть» задание слева, картинка справа (R2).
**Independent Test**: quickstart п. 2.

- [X] T013 [P] [US2] Тест разметки: в ответе `POST …/check` внутри `#exercise-solve` есть обёртка `.exercise-layout` с `:class` `with-source`, у самого `#exercise-solve` `:class` нет — `tests/integration/test_exercise_layout.py`
- [X] T014 [US2] Перенести сетку и `:class="{ 'with-source': picture }"` на внутреннюю обёртку `<div class="exercise-layout">` без `id` (x-data остаётся на `#exercise-solve`) — `src/french_learning/web/templates/exercises/solve.html`
- [X] T015 [US2] CSS: `.exercise.with-source …` → `.exercise-layout.with-source …` (сетка, sticky картинки, порядок столбцов ≥ 900 px, узкий экран) — `src/french_learning/web/static/css/screens.css`
- [X] T016 [US2] Найти другие блоки с `id` + `:class` / `x-bind:class` + `hx-swap="outerHTML"` (карточка повторения, тренажёры, `partials/exercise.html`) и исправить так же — `src/french_learning/web/templates/**`
- [X] T017 [US2] Проверка на демо 1400 px и 375 px: до / после «Проверить», «Сбросить» — класс и координаты блоков те же; картинка закрытая остаётся закрытой

## Phase 5: US3 — Озвучка звучит целиком (P1)

**Goal**: 0,35 с тишины в начале звука, перезапуск с начала (R3).
**Independent Test**: quickstart п. 3.

- [X] T018 [P] [US3] Тест: первый 0,35 с звука от `PiperSpeech.audio` (подменённый движок) — тишина, затем речь; ключ кеша изменился (старый файл не используется) — `tests/unit/practice/test_tts.py`
- [X] T019 [US3] Тишина 0,35 с в начале (кадры нулей с частотой и форматом голоса) при синтезе; в ключ кеша добавить версию `pad1` — `src/french_learning/practice/tts.py`
- [X] T020 [US3] `speech.js`: при нажатии `audio.pause(); audio.currentTime = 0; audio.play()` — слово всегда с начала — `src/french_learning/web/static/js/speech.js`
- [X] T021 [US3] Проверка на демо: `/tts?text=maison` отдаёт новый файл, длительность больше на 0,35 с

## Phase 6: US4 — «Задания 6/10» (P2)

**Independent Test**: quickstart п. 1.

- [X] T022 [P] [US4] Тест: панель урока с 2 классными и 3 домашними (без резерва) — «Задания» и «2/3», `title="в классе: 2, дома: 3"`; без домашки — «2/0» — `tests/integration/test_lesson_layout.py`
- [X] T023 [US4] `_counts`: `tasks_class`, `tasks_homework` (резерв не считается, домашние — все) — `src/french_learning/web/routes/lessons.py`
- [X] T024 [US4] Панель: счётчик «{класс}/{дом}» с подсказкой — `src/french_learning/web/templates/lesson_base.html`

## Phase 7: US5 — Клавиши на странице слова (P2)

**Independent Test**: quickstart п. 5.

- [X] T025 [US5] Расширить `keydown` в `vocab/entry.html`: `ArrowDown` → `details.entry-extra` открыть, `ArrowUp` → закрыть (на странице слова ↓ и ↑ всегда `preventDefault` — страница этими клавишами не прокручивается), `Enter` → `click()` по кнопке `[data-speak]` карточки; не срабатывать в `input, textarea, select, [contenteditable]`, при `dialog[open]`, при фокусе на `button, a, summary` (для Enter) и с модификаторами — `src/french_learning/web/templates/vocab/entry.html`
- [X] T026 [US5] Тест разметки: на странице слова есть `details.entry-extra` и кнопка `[data-speak]` внутри карточки (опора для клавиш) — `tests/integration/test_vocab_pages.py`
- [X] T027 [US5] Проверка на демо: ↓ / ↑ / ↑ / Enter, ← / → по-прежнему листают; в поле правки клавиши не перехватываются

## Phase 8: US6 — «Темы → Лексика» только со словами (P2)

**Independent Test**: quickstart п. 6.

- [X] T028 [P] [US6] Тест: `/topics` — тема раздела «Лексика» только с упражнением не показана; тема со словами — есть; `/topics/{id}` пустой темы открывается (200) — `tests/integration/test_topics_pages.py`
- [X] T029 [US6] `topics_by_section`: для раздела `vocabulary` — только темы хотя бы с одним нескрытым словом — `src/french_learning/content/index.py`

## Phase 9: US7 — Повторение последнего урока с главной (P2)

**Independent Test**: quickstart п. 7.

- [X] T030 [P] [US7] Тесты: блок «Повторение слов» — «N слов урока L», где L — наибольший номер урока с нескрытыми словами (у урока без слов берётся предыдущий); форма `POST /practice/start` с `mode=lesson`, `lesson=L`, `direction=ru_fr`; старт → сеанс из N карточек ru→fr; без слов — блок как при пустом словаре — `tests/integration/test_today.py`
- [X] T031 [US7] `build_today`: `last_lesson`, `last_lesson_words` — `src/french_learning/web/today.py`
- [X] T032 [US7] Блок на главной: число слов урока, кнопка «Повторить» — форма `mode=lesson&lesson=L&direction=ru_fr` (число слов — все слова урока) — `src/french_learning/web/templates/today.html`
- [X] T033 [US7] Старт с главной: `mode=lesson`, все слова урока (лимит «слов за подход» не обрезает — передать лимит = числу слов), способ ответа — значение по умолчанию страницы настройки (переворот карточки) — `src/french_learning/web/routes/vocab.py`

## Phase 10: US8 — «Числа»: словами → цифрами (P3)

**Independent Test**: quickstart п. 8.

- [X] T034 [P] [US8] Тесты генератора: вопрос `numbers-fr:75` — prompt `soixante-quinze` (основное написание `spellings(75)[0]`), ответы `("75",)`, подсказка «напишите цифрами»; `in_range` понимает `numbers:` и `numbers-fr:` — `tests/unit/trainers/test_generators.py`
- [X] T035 [P] [US8] Тесты страницы: настройка «Чисел» — выбор формата («цифрами → словами» по умолчанию / «словами → цифрами»); старт с `format=words_to_digits` и диапазоном 70–99 → только `numbers-fr:` 70–99; ответ « 75 » — верно, «57» — ошибка с ответом; без `format` — как раньше — `tests/integration/test_trainers_builtin.py`
- [X] T036 [US8] Генератор: вопросы `numbers-fr:N`; `in_range` для обоих префиксов — `src/french_learning/trainers/generators/numbers.py`
- [X] T037 [US8] Параметр сеанса `format` (`digits_to_words` | `words_to_digits`) фильтрует вопросы по префиксу; сохраняется в параметрах сеанса — `src/french_learning/web/routes/trainers.py`
- [X] T038 [US8] Радио «Формат» в настройке тренажёра «Числа» — `src/french_learning/web/templates/trainers/setup.html`
- [X] T039 [US8] Проверить, что счётчики «Чисел» в «Практике» и `trainers-list` не удвоились неожиданно (при необходимости считать по основному формату) — `src/french_learning/web/routes/trainers.py`, `tests/unit/trainers/test_catalog.py`

## Phase 11: US9 — Теория по строкам (P3)

- [X] T040 [US9] Раздел «Оформление теории» в общих правилах разбора: каждый пример (предложение, фраза) — своей строкой, никогда два в одной; слова для изучения — список «mot — перевод», одно слово на строку, не через запятую; пример «плохо / хорошо»; уже загруженную теорию не переделывать — `.claude/skills/_shared/content-rules.md`
- [X] T041 [US9] Ссылка на новое правило в шаге оформления теории навыков `/add-lesson` и `/add-material` (если правила подключаются там явно) — `.claude/skills/add-lesson/SKILL.md`, `.claude/skills/add-material/SKILL.md`

## Phase 12: Polish

- [X] T042 Запись в CLAUDE.md (раздел 012: где что лежит — `.exercise-layout`, тишина звука, удаление любых слов, формат «Чисел»)  — `CLAUDE.md`
- [X] T043 `uv run ruff format .`, `uv run ruff check .`, `uv run pytest`, `uv run python scripts/check_no_content.py`
- [X] T044 Полная проверка по `quickstart.md` на демо (8010), скриншоты для пользователя
- [X] T045 Дорожная карта: статус 012 «на приёмке», «Текущее состояние» — `docs/roadmap.md`

## Dependencies

- T003 → US1, US6, US7.
- Истории независимы друг от друга; US1 до US7 желательно (счёт слов урока без скрытых).
- Внутри истории: тесты → код → проверка на демо.

## Parallel Examples

- Тесты разных историй (T004–T006, T013, T018, T022, T028, T030, T034–T035) — в разных файлах, можно писать параллельно.
- US2 (шаблон + CSS), US3 (tts.py + speech.js), US8 (генератор) — не пересекаются по файлам.

## Implementation Strategy

1. MVP — P1: US1, US2, US3 (то, что мешает каждый день).
2. Затем P2: US4–US7; затем P3: US8, US9.
3. Показ на демо одним заходом после всех историй; CHANGELOG «на приёмке» до «принимаю».
