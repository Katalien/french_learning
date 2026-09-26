---

description: "Задачи реализации функции 001 — формат, хранилище и просмотр уроков"
---

# Tasks: Формат, хранилище и просмотр уроков

**Input**: `specs/001-lesson-content-view/` — plan.md, spec.md, research.md, data-model.md,
contracts/content-format.md, contracts/ui-routes.md, quickstart.md

**Prerequisites**: plan.md, spec.md (обязательны); остальные документы — источники деталей

**Tests**: ОБЯЗАТЕЛЬНЫ — конституция, принцип XIII (TDD): тест пишется первым и должен упасть
до реализации. Интерфейс дополнительно проверяется вручную по quickstart.md.

**Organization**: задачи сгруппированы по пользовательским историям; каждая история — отдельно
проверяемый шаг.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно (разные файлы, нет зависимости от незавершённых задач)
- **[Story]**: история из spec.md (US1…US5)

## Path Conventions

Один проект: пакет `src/french_learning/`, тесты `tests/` в корне репозитория (plan.md).

---

## Phase 1: Setup (общая инфраструктура)

**Purpose**: создать проект, инструменты качества и защиту от попадания контента в репозиторий

- [X] T001 Создать проект uv с раскладкой `src/`: `pyproject.toml` (Python 3.12, зависимости: fastapi, uvicorn, jinja2, pydantic, pydantic-settings, pyyaml, markdown-it-py, mdit-py-plugins, nh3, mammoth, python-multipart; dev: pytest, httpx, ruff, pre-commit, python-docx), точка входа `french-learning = "french_learning.cli:main"`, пустые `src/french_learning/__init__.py`, `uv.lock`
- [X] T002 [P] Настроить ruff (check + format, line-length 100) и pytest (`testpaths = ["tests"]`) в `pyproject.toml`
- [X] T003 [P] Дополнить `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `*.sqlite`, `.pytest_cache/`, `.ruff_cache/`; создать `.env.example` с `CONTENT_DIR=`, `SOURCE_MATERIALS_DIR=`, `HOST=127.0.0.1`, `PORT=8000` (без реальных путей-секретов)
- [X] T004 [P] Тест защиты от контента в `tests/unit/test_no_content_guard.py`: скрипт находит запрещённые файлы (изображения, pdf, docx, audio/video, yaml контента) вне разрешённых путей `tests/fixtures/`, `src/french_learning/web/static/`
- [X] T005 Скрипт защиты `scripts/check_no_content.py` (выход 1 при нарушении) — после T004
- [X] T006 [P] `.pre-commit-config.yaml`: ruff check и ruff format (стадия pre-commit), `scripts/check_no_content.py` (pre-commit), `uv run pytest` (стадия pre-push)
- [X] T007 [P] GitHub Actions `.github/workflows/ci.yml`: на push и pull_request — установка uv, `uv sync`, `ruff check .`, `ruff format --check .`, `python scripts/check_no_content.py`, `pytest`
- [X] T008 [P] Положить закреплённые версии htmx, Alpine.js, Pico CSS в `src/french_learning/web/static/vendor/` с файлами лицензий и `VERSIONS.md` (источник, версия)
- [X] T009 [P] Создать `README.md` (что это, требования, установка `uv sync`, настройка `.env`, запуск — заполняется в T063) и `CHANGELOG.md` (раздел «Unreleased»); обновить статус функции 001 в `docs/roadmap.md`: 📝 → 🛠 (конституция, «Документация»)

**Checkpoint**: `uv sync`, `ruff check .`, `pytest` (1 тест) и хуки работают; CI зелёный

---

## Phase 2: Foundational (блокирует все истории)

**Purpose**: формат контента, загрузка, индекс, отрисовка, каркас веб-приложения

**⚠️ CRITICAL**: работа над историями начинается только после этой фазы

### Синтетический контент-образец

- [X] T010 Создать придуманный образец (НЕ материалы преподавателя) в `tests/fixtures/content/` по contracts/content-format.md: `format.yaml`, `topics.yaml` (3 раздела, 5 тем), `lessons/001/`, `lessons/002/` и `lessons/004/` (пропуск номера 3) с `lesson.yaml` (у урока 2 без даты и с одним медиафайлом `video`; в уроке 4 все упражнения домашки со статусом `reserve`, теории нет), теорией с таблицей и встроенной картинкой, текстом с двумя упражнениями к нему, упражнениями всех 10 типов (`gap_choice`, `gap_input`, `multi_gap`, `transform`, `true_false`, `choice`, `two_forms`, `grouping`, `picture`, `open`) в частях `class` и `homework`, статусами `main` / `optional` / `reserve`, справкой, пунктом с `needs_review`, упражнением на повторение темы урока 1 внутри урока 2; `vocabulary/` (слово новое в уроке 1 и повторяющееся в уроке 2; слово, встреченное в упражнении урока 1, но впервые в лексике урока 2); `extra/` с элементом без урока; `reports/` с одним открытым сообщением; `sources/` с маленькими сгенерированными jpg, pdf, docx; один намеренно повреждённый файл упражнения `lessons/002/exercises/ex-broken00.yaml`

### Схема формата (TDD)

- [X] T011 [P] Тесты схемы в `tests/unit/test_schema.py`: `Id` соответствует `^(les|th|tx|ex|voc|top|rep)-[a-z2-7]{8}$`; `Part` ∈ {class, homework}; `Origin` ∈ {material, external, user, ai, service}; `Status` ∈ {main, optional, reserve}; `needs_review.note` обязателен при `flag: true`; `part` обязателен при наличии `lesson` (кроме vocab); `topics` ≥ 1, кроме `needs_review.flag = true`; `sources` ≥ 1, кроме `origin = user`; для упражнений: число `{{N}}` в тексте совпадает с ключами `answers`, ответы `gap_choice` ∈ `options`, `multi_gap` ≥ 2 пропуска, индексы `choice` в пределах вариантов, `picture` → `show_source: true`, `open` — без ответов, `number` ≥ 1
- [X] T012 Реализовать модели формата версии 1 в `src/french_learning/content/schema.py` (`FORMAT_VERSION = 1`; Lesson, Media, Theory, Text, Exercise с пунктами по типам, VocabEntry со всеми полями data-model.md, Topic, Section, Report) — тесты T011 проходят

### Настройки (TDD)

- [X] T013 [P] Тесты настроек в `tests/unit/test_config.py`: значения по умолчанию `HOST=127.0.0.1`, `PORT=8000`; `CONTENT_DIR` читается из окружения и `.env`; отсутствие `CONTENT_DIR` не падает, а даёт признак «не настроено»
- [X] T014 Реализовать `src/french_learning/config.py` (pydantic-settings) — тесты T013 проходят

### Загрузчик (TDD)

- [X] T015 [P] Тесты загрузчика в `tests/unit/test_loader.py`: образец T010 загружается; повреждённый файл даёт `LoadError(path, message)`, остальные элементы загружены; дубли id, ссылки на несуществующие темы / тексты / теорию / элементы в сообщениях, отсутствующие `sources[].file`, повтор `number` в паре (урок, часть), повтор номера урока, неподдерживаемая `format_version` — дают ошибки загрузки; файлы вне описанной структуры игнорируются
- [X] T016 Реализовать `src/french_learning/content/loader.py` (обход дерева, YAML и Markdown с шапкой, валидация, изоляция ошибок, правила 1–8 из contracts/content-format.md) — тесты T015 проходят

### Индекс (TDD)

- [X] T017 [P] Тесты индекса в `tests/unit/test_index.py`: уроки по номеру (новые сверху); элементы по (урок, часть, вид); темы урока = объединение тем элементов (включая упражнение на повторение); тема → элементы из всех уроков и `extra/`; обратные связи текст / теория → упражнения; список `needs_review` (элементы и пункты); правило новых слов FR-039 (`min(lessons) == L` → новое; встреча в упражнении не учитывается); перестройка индекса при изменении отпечатка дерева файлов
- [X] T018 Реализовать `src/french_learning/content/index.py` (индекс в памяти + отпечаток по времени изменения файлов, research R7) — тесты T017 проходят

### Отрисовка (TDD)

- [X] T019 [P] Тесты отрисовки в `tests/unit/test_render.py`: Markdown с таблицей → HTML-таблица; `<script>` и обработчики событий удаляются; относительный путь картинки `sources/x.jpg` превращается в `/sources/lessons/NNN/sources/x.jpg`; docx из образца → HTML с текстом
- [X] T020 Реализовать `src/french_learning/content/render.py` (markdown-it-py + таблицы, nh3, mammoth) — тесты T019 проходят

### Каркас веб-приложения и команды (TDD)

- [X] T021 [P] Интеграционные тесты каркаса в `tests/integration/test_app.py`: без `CONTENT_DIR` любая страница показывает объяснение, где задать путь; с образцом `GET /` отвечает 200; `GET /problems` показывает повреждённый файл и причину; статические файлы vendor отдаются; ни один шаблон не подключает внешние скрипты, стили или шрифты по `http(s)://` (FR-052, работа без интернета)
- [X] T022 [P] Тесты команд в `tests/integration/test_cli.py`: `validate-content` на образце печатает одно нарушение (повреждённый файл) и завершается с кодом 1; на образце без повреждённого файла — «Нарушений нет» и код 0; `serve` по умолчанию использует хост `127.0.0.1`
- [X] T023 Реализовать фабрику приложения `src/french_learning/web/app.py` (FastAPI, Jinja2, статические файлы, загрузка индекса, проверка отпечатка перед запросом, страница «хранилище не настроено»)
- [X] T024 Базовый шаблон `src/french_learning/web/templates/base.html` (русский язык, подключение vendor-файлов, мобильная вёрстка) и стили `src/french_learning/web/static/css/app.css` (ширина от 375 px без горизонтальной прокрутки, цвета пометок)
- [X] T025 Страница ошибок загрузки `src/french_learning/web/routes/problems.py` и шаблон `templates/problems.html` (FR-005)
- [X] T026 Реализовать `src/french_learning/cli.py`: `serve` (uvicorn на `HOST`/`PORT`), `validate-content` (формат вывода: файл, поле, сообщение; коды 0/1) — тесты T021, T022 проходят
- [X] T027 [P] Интерфейс прогресса `src/french_learning/content/progress.py`: `homework_done(lesson) -> int` возвращает 0 (заменится в 004) + тест в `tests/unit/test_progress.py`

**Checkpoint**: формат, загрузка, индекс, отрисовка и каркас готовы; `validate-content` работает

---

## Phase 3: User Story 1 — Открыть урок и увидеть его содержимое (Priority: P1) 🎯 MVP

**Goal**: список уроков со сводками → урок → разделы → вкладки «В классе» / «Домашка» →
просмотр упражнения

**Independent Test**: на образце открыть главную → урок 2 → «Задания» → «Домашка» → открыть
упражнение; ответы не видны, справка скрыта, у «по картинке» исходник рядом

### Tests for User Story 1 ⚠️ (пишутся первыми и должны упасть)

- [X] T028 [P] [US1] Тесты сводки урока в `tests/unit/test_lesson_summary.py`: номер, дата или «дата не указана», темы урока, число новых слов (FR-039), домашка «X из Y» — Y = только `main` упражнения `homework`, отдельный счётчик `optional`, `reserve` не учитывается (FR-031), число «требует проверки»
- [X] T029 [P] [US1] Интеграционные тесты страниц в `tests/integration/test_lessons_pages.py`: `GET /` — уроки 4, 2 и 1 (новые сверху, пропуск номера 3 без ошибок) со сводками и ссылками на темы и «Дополнительные материалы»; `GET /lessons/4/tasks?part=homework` — сообщение, что основных заданий нет, и ссылка на «Резерв»; `GET /lessons/4/theory` — сообщение «нет материалов»; `GET /lessons/2` — разделы «Теория», «Тексты», «Задания»; `GET /lessons/2/tasks?part=homework` — названия «номер — тема — описание» и «на листе: …», пометка «необязательное», упражнения `reserve` отсутствуют; `GET /lessons/2/reserve` — только резерв; урок без домашки — сообщение «нет материалов»
- [X] T030 [P] [US1] Интеграционные тесты упражнения в `tests/integration/test_exercise_view.py`: `GET /elements/{id}` для каждого из 10 типов показывает формулировку `instruction.ru` и пункты с пропусками; в ответе нет правильных ответов (FR-023); справка присутствует свёрнутой (FR-024); у `picture` показан исходный файл (FR-025); повреждённый элемент — карточка «ошибка в данных» со ссылкой на `/problems`

### Implementation for User Story 1

- [X] T031 [US1] Подсчёт сводки урока в `src/french_learning/content/index.py` (функция `lesson_summary`) — тесты T028 проходят
- [X] T032 [US1] Маршруты `GET /`, `GET /lessons/{number}`, `/tasks`, `/reserve` в `src/french_learning/web/routes/lessons.py`
- [X] T033 [US1] Шаблоны `templates/home.html`, `templates/lesson.html`, `templates/partials/lesson_summary.html`, `templates/partials/task_list.html` (вкладки «В классе» / «Домашка» через HTMX)
- [X] T034 [US1] Маршрут `GET /elements/{id}` в `src/french_learning/web/routes/elements.py` и шаблоны отображения упражнений всех типов `templates/partials/exercise/*.html` (пропуски `{{N}}` — пустые места без ответов; справка — раскрываемый блок Alpine.js; `picture` — исходник рядом, на узком экране сверху)
- [X] T035 [US1] Проверка по независимому тесту US1 — тесты T029, T030 проходят

**Checkpoint**: US1 работает сама по себе — можно показать пользователю

---

## Phase 4: User Story 2 — Изучить теорию и тексты урока (Priority: P2)

**Goal**: теория как форматированный текст, лексика «новые / на повторение», тексты отдельно,
«открыть оригинал»

**Independent Test**: урок 1 → «Теория» → таблица и картинка; «открыть оригинал» открывает
PDF; лексика разделена; «Тексты» → текст со ссылками на упражнения и обратно

### Tests for User Story 2 ⚠️

- [X] T036 [P] [US2] Интеграционные тесты в `tests/integration/test_theory_texts.py`: `GET /lessons/1/theory` — таблица и картинка из теории, лексика с артиклем (`la maison`), разделение «новые» / «на повторение» по FR-039; `GET /lessons/1/texts` — текст отдельным элементом со ссылками на упражнения; страница упражнения к тексту содержит ссылку на текст, а упражнения, связанного с теорией, — ссылку на теорию; страница теории содержит ссылки на связанные упражнения (FR-027, обе связи); у элемента теории с 3 и более заголовками есть оглавление со ссылками на заголовки (Edge Cases)
- [X] T037 [P] [US2] Тесты отдачи исходников в `tests/integration/test_sources.py`: jpg и pdf отдаются с верным типом; docx отдаётся как HTML; путь с `..` или вне хранилища → 404; отсутствующий файл → сообщение «оригинал недоступен», элемент при этом открывается

### Implementation for User Story 2

- [X] T038 [US2] Маршруты `/lessons/{number}/theory` и `/texts` в `src/french_learning/web/routes/lessons.py` + шаблоны `templates/theory.html` (с оглавлением для теории с 3+ заголовками и ссылками на связанные упражнения), `templates/texts.html`, `templates/partials/vocab_list.html`
- [X] T039 [US2] Маршрут `GET /sources/{path}` в `src/french_learning/web/routes/sources.py` (проверка пути внутри `CONTENT_DIR`, docx → HTML через render.py) и кнопка «Открыть оригинал» у каждого элемента в `templates/partials/element_actions.html`
- [X] T040 [US2] Проверка по независимому тесту US2 — тесты T036, T037 проходят

**Checkpoint**: US1 + US2 работают

---

## Phase 5: User Story 3 — Повторить тему через все уроки (Priority: P3)

**Goal**: темы по разделам, страница темы по всем урокам, «Дополнительные материалы»,
правка тем и даты урока с записью в файлы и git-коммитом

**Independent Test**: темы → тема, общая для уроков 1 и 2 → элементы обоих уроков и
дополнительный материал; переименовать тему → новое имя везде, коммит в хранилище

### Tests for User Story 3 ⚠️

- [ ] T041 [P] [US3] Тесты записи в `tests/unit/test_writer.py` (на временной копии образца с `git init`): атомарная запись (при ошибке файл не повреждён); изменение даты урока; изменение тем элемента (выбор существующей и создание новой темы, имя уникально без учёта регистра); переименование темы меняет только `topics.yaml`; объединение A → B заменяет ссылки во всех элементах и удаляет A; каждая операция — один git-коммит с понятным сообщением; после коммита выполняется попытка `git push` (резервная копия, конституция VI): при отсутствии удалённого репозитория или сети правка сохраняется, а пользователь видит предупреждение «копия не отправлена»; при отсутствии git-репозитория запись выполняется, а коммит пропускается с предупреждением
- [ ] T042 [P] [US3] Интеграционные тесты в `tests/integration/test_topics_pages.py`: `GET /topics` — темы по разделам с числом элементов и «Без темы»; `GET /topics/{id}` — элементы обоих уроков с номером урока и элемент без урока с пометкой «дополнительный материал»; `GET /extras` — только элементы без урока; POST-действия rename / merge / date / topics меняют страницы сразу

### Implementation for User Story 3

- [ ] T043 [US3] Реализовать `src/french_learning/content/writer.py` (атомарная запись YAML и шапки Markdown с сохранением остального содержимого; git-коммит через subprocess в `CONTENT_DIR`; затем попытка `git push`, неудача не прерывает правку и показывается предупреждением) — тесты T041 проходят
- [ ] T044 [US3] Маршруты `/topics`, `/topics/{id}`, `/topics/{id}/rename`, `/topics/{id}/merge` в `src/french_learning/web/routes/topics.py` + шаблоны `templates/topics.html`, `templates/topic.html`
- [ ] T045 [US3] Маршрут `/extras` в `src/french_learning/web/routes/extras.py` + шаблон `templates/extras.html` (FR-038)
- [ ] T046 [US3] Действия `/lessons/{number}/date` и `/elements/{id}/topics` + фрагменты форм `templates/partials/edit_date.html`, `templates/partials/edit_topics.html` (HTMX)
- [ ] T047 [US3] Проверка по независимому тесту US3 — тесты T042 проходят

**Checkpoint**: US1–US3 работают

---

## Phase 6: User Story 4 — Понимать, чему можно доверять (Priority: P4)

**Goal**: переключатель происхождения, значок «требует проверки» с пояснением, общий список,
«отметить проверенным», сообщения об ошибках с напоминанием и счётчиком

**Independent Test**: включить переключатель → метки и оригинальная формулировка; раскрыть
значок → пояснение; отметить проверенным → пометка снята; отправить сообщение → напоминание,
счётчик на главной +1

### Tests for User Story 4 ⚠️

- [ ] T048 [P] [US4] Тесты в `tests/unit/test_writer_review.py`: снятие `needs_review` у элемента и у пункта упражнения; создание сообщения `reports/rep-….yaml` с полями `id`, `element`, `item`, `comment`, `created`, `status: open`, `resolution: null`; git-коммит
- [ ] T049 [P] [US4] Интеграционные тесты в `tests/integration/test_trust.py`: по умолчанию меток происхождения нет; после `POST /settings/origin` (cookie) метки видны у 100% элементов, у формулировки — оригинал; значок «требует проверки» раскрывает `note`; `GET /review` — все элементы и пункты с пометкой; `POST /elements/{id}/verified` снимает пометку; `POST /elements/{id}/report` — ответ содержит напоминание «сообщения разбирает агент» и команду; `GET /` показывает число открытых сообщений; `GET /reports` — открытые сверху

### Implementation for User Story 4

- [ ] T050 [US4] Функции `mark_verified` и `create_report` в `src/french_learning/content/writer.py` — тесты T048 проходят
- [ ] T051 [US4] Переключатель происхождения: маршрут `POST /settings/origin` в `src/french_learning/web/routes/settings.py`, метки в `templates/partials/origin_badge.html`, оригинал формулировки в шаблонах упражнений
- [ ] T052 [US4] Значок и пояснение `templates/partials/review_badge.html` (Alpine.js), страница `GET /review` в `src/french_learning/web/routes/review.py` + `templates/review.html`, действие `verified`
- [ ] T053 [US4] Сообщения об ошибках: форма `templates/partials/report_form.html`, маршруты `/elements/{id}/report` и `GET /reports` в `src/french_learning/web/routes/reports.py` + `templates/reports.html`, напоминание после отправки, счётчик на главной
- [ ] T054 [US4] Проверка по независимому тесту US4 — тесты T049 проходят

**Checkpoint**: US1–US4 работают

---

## Phase 7: User Story 5 — Видеть медиафайлы урока (Priority: P5)

**Goal**: список аудио / видео урока с кнопкой «Скопировать путь»

**Independent Test**: урок 2 → список медиафайлов: имя, часть урока, путь; кнопка копирует путь

- [ ] T055 [P] [US5] Интеграционный тест в `tests/integration/test_media.py`: `GET /lessons/2` показывает медиафайл с именем, частью урока и полным путём (`SOURCE_MATERIALS_DIR` + `path`); урок без медиа — блок не показывается
- [ ] T056 [US5] Блок медиафайлов `templates/partials/media_list.html` с кнопкой «Скопировать путь» (Alpine.js, буфер обмена) — тест T055 проходит

**Checkpoint**: все истории работают

---

## Phase 8: Polish & Cross-Cutting

- [ ] T057 [P] Команда `french-learning demo-init <папка>` в `src/french_learning/cli.py`: копирует образец без повреждённого файла и с ним (флаг `--with-broken`) в указанную папку и выполняет `git init` + первый коммит; тест в `tests/integration/test_cli.py`
- [ ] T058 [P] Проверить все страницы на ширине 375 px и поправить `static/css/app.css` (SC-007)
- [ ] T059 [P] Сообщения интерфейса: проверить, что все тексты на русском, ошибки — понятные, без технических деталей (FR-050)
- [ ] T060 Полный прогон: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`, `python scripts/check_no_content.py`
- [ ] T061 Пройти quickstart.md на демо-хранилище `C:\Users\Kate\source\french_learning_demo` (создаётся T057) и исправить найденное
- [ ] T062 [P] Обновить `CLAUDE.md`, раздел «Команды»: `uv sync`, `uv run french-learning serve`, `uv run french-learning validate-content`, `uv run pytest`, `uv run ruff check .`
- [ ] T063 [P] Обновить `README.md` (установка, настройка `.env`, запуск, проверка контента, демо) и `CHANGELOG.md` (что появилось в 001)
- [ ] T064 После приёмки пользователем: статус функции 001 в `docs/roadmap.md` 🛠 → ✅; слить ветку `001-lesson-content-view` в `main` при проходящих тестах и отправить `main` на GitHub (конституция, «Контроль качества»: слияние только после приёмки)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → сразу
- **Foundational (Phase 2)** → после Setup; блокирует все истории
- **US1 (Phase 3)** → после Foundational; MVP
- **US2 (Phase 4)** → после Foundational; использует шаблоны и маршруты US1 (страница урока)
- **US3 (Phase 5)** → после Foundational; writer.py нужен US4
- **US4 (Phase 6)** → после US3 (использует writer.py)
- **US5 (Phase 7)** → после US1 (страница урока)
- **Polish (Phase 8)** → после всех нужных историй

### Within Each User Story

- Тесты → убедиться, что падают → реализация → тесты проходят
- Модели / индекс → маршруты → шаблоны
- Каждый checkpoint — коммит; при падающих тестах коммит невозможен (хуки)

### Parallel Opportunities

- Setup: T002, T003, T004, T006, T007, T008, T009 — параллельно после T001
- Foundational: тесты T011, T013, T015, T017, T019, T021, T022 — параллельно; реализации — по мере
  готовности своих тестов (T012 → T016 → T018)
- Внутри историй: все задачи тестов с [P] — параллельно

### Parallel Example: User Story 1

```text
Task: "T028 Тесты сводки урока в tests/unit/test_lesson_summary.py"
Task: "T029 Интеграционные тесты страниц в tests/integration/test_lessons_pages.py"
Task: "T030 Интеграционные тесты упражнения в tests/integration/test_exercise_view.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational
2. Phase 3 US1
3. **СТОП и проверка**: пользователь открывает демо-хранилище и смотрит список уроков, урок,
   задания — первая возможность увидеть настоящий интерфейс
4. Правки по замечаниям → дальше

### Incremental Delivery

1. Setup + Foundational → основа
2. US1 → показ пользователю (MVP)
3. US2 → теория и тексты
4. US3 → темы и правки
5. US4 → доверие и сообщения
6. US5 → медиа
7. Polish → quickstart → приёмка пользователем → слияние в `main`

---

## Notes

- Тестовые данные — только синтетические (конституция, принцип VI)
- Каждая задача или логическая группа — отдельный коммит в стиле `feat:` / `test:` / `chore:`
- Не обходить проверки (`--no-verify` запрещён)
- Остановка на каждом checkpoint для показа пользователю
