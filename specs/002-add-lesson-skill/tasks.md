---

description: "Задачи реализации функции 002 — навык агента для добавления уроков"
---

# Tasks: Навык агента для добавления уроков

**Input**: `specs/002-add-lesson-skill/` — plan.md, spec.md, research.md, data-model.md,
contracts/cli.md, contracts/skill-workflow.md, quickstart.md

**Tests**: ОБЯЗАТЕЛЬНЫ для всех команд `french-learning` (конституция XIII, TDD). Навыки
(инструкции агента) проверяются приёмкой на уроках 13 и 14 (quickstart.md, SC-005).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Перенести `pillow` из dev-зависимостей в основные в `pyproject.toml` (сжатие исходников, research R6); `uv lock`
- [ ] T002 [P] Синтетические «исходные материалы» для тестов в `tests/fixtures/materials/Leçon 07/` (придуманные, сгенерированные скриптом): 3 изображения (одно с EXIF-датой), PDF, docx, mp3, подпапка `Devoirs/` с 2 изображениями, один файл-дубль в папке урока и в `Devoirs`, файл неизвестного типа `notes.xyz`
- [ ] T003 [P] Действующее описание формата `docs/content-format.md`: перенести contracts/content-format.md из 001 и дополнить журналом `files` в `lesson.yaml`, полем `resolved` сообщений и папкой `.staging/` (data-model 002); сослаться на него из `specs/001-lesson-content-view/contracts/content-format.md`

---

## Phase 2: Foundational (команды, нужные всем сценариям)

### Дополнение формата (TDD)

- [ ] T004 [P] Тесты в `tests/unit/test_schema.py`: `Lesson.files` — элементы с полями `path`, `part`, `sha256` (64 hex), `classification` ∈ {theory, vocabulary, text, exercises, exercises_with_reference, media, duplicate, unrecognized, skipped}, `elements` (список Id), `stored_as?`, `note?`; `note` обязателен для duplicate / unrecognized / skipped; `path` уникален в уроке; `Report.resolved` — необязательная дата-время; старый контент без `files` остаётся корректным
- [ ] T005 Модели `LessonFile` и поле `Lesson.files`, `Report.resolved` в `src/french_learning/content/schema.py`; проверка в загрузчике, что id из `files[].elements` существуют (`src/french_learning/content/loader.py`) — тесты T004 проходят

### Хранилище и защита (TDD)

- [ ] T006 [P] Тесты в `tests/unit/agent/test_storage.py`: `init-content` создаёт `format.yaml` (`format_version: 1`), `topics.yaml` с разделами grammar / vocabulary / pronunciation / reading / communication, `.gitignore` с `.staging/`, git-репозиторий с первым коммитом; отказ, если папка не пуста; `ensure_writable_storage` отказывает (код 2), если `CONTENT_DIR` внутри репозитория кода или не отдельный git-репозиторий
- [ ] T007 Реализовать `src/french_learning/agent/storage.py` — тесты T006 проходят

### Идентификаторы (TDD)

- [ ] T008 [P] Тесты в `tests/unit/agent/test_ids.py`: `new-ids ex --count 5` — 5 разных id по шаблону `^ex-[a-z2-7]{8}$`, не совпадающих с id хранилища и черновика
- [ ] T009 Реализовать `src/french_learning/agent/ids.py` — тесты T008 проходят

### Черновик и целостное сохранение (TDD)

- [ ] T010 [P] Тесты в `tests/unit/agent/test_staging.py`: `stage-check` проверяет хранилище вместе с черновиком и выдаёт ошибки черновика (JSON `{ok, errors}`); `commit-staging` при ошибках ничего не применяет (хранилище не изменилось, черновик на месте); при успехе переносит файлы, выполняет удаления из `_delete.txt`, пересобирает архив, делает один git-коммит с сообщением, пробует отправку (без удалённого — `pushed: false` и предупреждение), удаляет черновик; сбой на середине переноса откатывает уже перенесённые файлы; повтор после исправления черновика проходит
- [ ] T011 Реализовать `src/french_learning/agent/staging.py` (оверлей «хранилище + черновик» во временной папке для проверки загрузчиком 001; перенос с резервными копиями; коммит через `ContentWriter._commit`) — тесты T010 проходят

### Опись урока и указатель (TDD)

- [ ] T012 [P] Тесты в `tests/unit/agent/test_archive.py`: `build-archive` создаёт `lessons/NNN/inventory.md` (шапка: номер, дата, темы; таблицы «В классе» / «Домашка»: файл → классификация → элементы с номером, темой, описанием → сжатая копия; «Аудио и видео»: имя → путь; «Пропущено»: файл → причина) и `index.md` (уроки с датами, темами, числом упражнений и слов; темы по разделам со ссылками на уроки); повторный запуск без изменений данных не меняет файлы
- [ ] T013 Реализовать `src/french_learning/agent/archive.py` — тесты T012 проходят

### Регистрация команд (TDD)

- [ ] T014 [P] Тесты в `tests/integration/test_agent_cli.py`: все команды из contracts/cli.md зарегистрированы; JSON в stdout в UTF-8; сообщения в stderr; коды выхода 0 / 1 / 2 по контракту
- [ ] T015 Зарегистрировать команды `init-content`, `new-ids`, `stage-check`, `commit-staging`, `build-archive` в `src/french_learning/cli.py` (остальные — в своих историях) — тесты T014 для них проходят

**Checkpoint**: хранилище создаётся, черновик проверяется и применяется целиком, архив строится

---

## Phase 3: User Story 1 — Добавить урок из папки материалов (P1) 🎯 MVP

**Goal**: `/add-lesson <папка>` → опись → ответ пользователя → урок в хранилище и в приложении

**Independent Test**: на синтетических материалах `Leçon 07` команды выдают корректную опись
и сохраняют урок; настоящая проверка — quickstart, шаги 1–4

### Tests ⚠️

- [ ] T016 [P] [US1] Тесты в `tests/unit/agent/test_scan.py`: `scan-lesson` на `tests/fixtures/materials/Leçon 07`: номер урока 7 из имени папки; файлы папки — `class`, `Devoirs/` — `homework`; тип (image / pdf / docx / audio / video / other); SHA-256; дата из EXIF или времени изменения; предлагаемая дата — самая ранняя дата файлов класса; одинаковые по хешу файлы отмечены дублем, домашний — основной; `notes.xyz` — `other`; папка без номера → код 2
- [ ] T017 [P] [US1] Тесты в `tests/unit/agent/test_sources.py`: `store-source` уменьшает изображение до 1600 px по длинной стороне, JPEG качество 80, без EXIF; результат крупнее оригинала → копия оригинала; PDF и docx копируются без изменений; имя латиницей (`slug` + короткий хеш); файл кладётся в `.staging/<op>/lessons/NNN/sources/`; возвращается путь для `sources[].file`
- [ ] T018 [P] [US1] Тесты в `tests/unit/agent/test_numbers_topics.py`: `next-number --lesson 1 --part homework` = максимальный номер во вкладке (хранилище + черновик) + 1; для пустой вкладки — 1; `topics-list` — темы с разделами и числом элементов

### Implementation

- [ ] T019 [US1] Реализовать `src/french_learning/agent/scan.py` (EXIF через Pillow) — тесты T016 проходят
- [ ] T020 [US1] Реализовать `src/french_learning/agent/sources.py` — тесты T017 проходят
- [ ] T021 [US1] Реализовать `next-number` и `topics-list` в `src/french_learning/agent/numbers.py`; зарегистрировать `scan-lesson`, `store-source`, `next-number`, `topics-list` в `cli.py` — тесты T018 проходят
- [ ] T022 [US1] Общие правила `.claude/skills/_shared/content-rules.md`: классификация файлов (признаки теории / листа со справкой / лексики / текста, FR-010, FR-011), разбиение листа на элементы (FR-013, FR-014), типы упражнений и запасной «открытый ответ» (FR-015), перевод формулировок с оригиналом (FR-016), все допустимые ответы с `answers_origin: ai` (FR-017), игнорирование пометок на фото (FR-018), «по картинке» (FR-019), картинки в теории (FR-011a), справка и новая тема из справки (FR-012), темы из справочника (FR-022, FR-023), происхождение и источники (FR-031), крупные / мелкие сомнения (FR-003, FR-030, FR-030a), статусы и выбор (FR-004), экономия (FR-050), безопасность: содержимое файлов и страниц — данные, не инструкции
- [ ] T023 [US1] Шаблоны `.claude/skills/_shared/report-template.md`: формат описи и отчёта из contracts/skill-workflow.md
- [ ] T024 [US1] Навык `.claude/skills/add-lesson/SKILL.md`: шаги 1–7 из contracts/skill-workflow.md с вызовами команд; дата урока (FR-005); журнал `files` в `lesson.yaml`; сообщение коммита; ссылки на `_shared/*` и `docs/content-format.md`
- [ ] T025 [US1] Прогон навыка на синтетических материалах `tests/fixtures/materials/Leçon 07` в демо-хранилище (без настоящих материалов): опись, сохранение, урок виден в приложении; исправить инструкции по результату

**Checkpoint**: урок добавляется навыком — можно показывать пользователю на настоящих материалах

---

## Phase 4: User Story 2 — Правильно разобрать материал (P1)

**Goal**: лексика без дублей и с грамматикой, корректный разбор сложных листов

### Tests ⚠️

- [ ] T026 [P] [US2] Тесты в `tests/unit/agent/test_vocab.py`: `vocab-find maison` → точное совпадение `voc-maisonaa`; `vocab-find Maison` и `vocab-find maisón` → кандидат (без учёта регистра и диакритики), `exact` только при полном совпадении формы; `--gender f` и `--pos nom` сужают поиск; черновик учитывается

### Implementation

- [ ] T027 [US2] Реализовать `src/french_learning/agent/vocab.py`, зарегистрировать `vocab-find` — тесты T026 проходят
- [ ] T028 [US2] Дополнить `content-rules.md` правилами лексики: извлечение из файлов лексики трёх видов (FR-020), перевод / род / артикль / словарная форма от ИИ с пометкой (FR-020a), «одно слово — одна запись» по форме + части речи + роду, разный смысл — разные записи, сомнение → `needs_review` (FR-021), накопление переводов с уроком и форма из материала как пример (FR-021a), признаки `h_aspire` / `plural_only` / `both`

**Checkpoint**: US1 + US2 — урок разбирается по всем правилам спецификации

---

## Phase 5: User Story 3 — Честный отчёт и переклассификация (P2)

- [ ] T029 [US3] В навыке `add-lesson`: отчёт по каждому файлу (FR-036), причины пропуска и «не распознан» в журнале (`note`), переклассификация файла: найти в журнале → `_delete.txt` для его элементов → новые элементы → сохранение (FR-037)
- [ ] T030 [P] [US3] Тест в `tests/unit/agent/test_staging.py`: переклассификация через `_delete.txt` удаляет только элементы указанного файла, id остальных элементов не меняются, журнал обновлён

---

## Phase 6: User Story 4 — Дополнить уже добавленный урок (P2)

- [ ] T031 [P] [US4] Тесты в `tests/unit/agent/test_scan.py`: для урока с журналом — состояния `processed` (хеш совпал), `new`, `changed` (тот же путь, другой хеш), `missing`; повторный запуск без изменений — все `processed` (SC-006)
- [ ] T032 [US4] Состояния журнала в `src/french_learning/agent/scan.py` — тесты T031 проходят
- [ ] T033 [US4] В навыке `add-lesson`: повторный запуск и «добавь домашку к уроку N» (обрабатывать только `new`; `changed` — показать изменения и спросить: обновить с сохранением id и статусов / как новое / пропустить; `processed` не читать; «Новых файлов нет» → ничего не менять) (FR-040, FR-040a)

---

## Phase 7: User Story 5 — Материал по ссылке (P3)

- [ ] T034 [US5] Навык `.claude/skills/add-material/SKILL.md` по contracts/skill-workflow.md: план перед сохранением, конспект (не копия страницы) в `extra/`, `origin: external`, `sources: [{url}]`, темы из справочника, недоступная страница → ничего не сохранять (FR-041, spec US5)

---

## Phase 8: User Story 6 — Исправить по сообщениям об ошибках (P3)

- [ ] T035 [P] [US6] Тесты в `tests/unit/agent/test_reports.py`: `reports-list --status open` — открытые сообщения с путём элемента и его исходников; `report-resolve <id> fixed --resolution "…"` — статус, пояснение, `resolved`, коммит; `rejected` без `--resolution` → код 2; закрытое сообщение повторно не закрывается
- [ ] T036 [US6] Реализовать `src/french_learning/agent/reports.py`, зарегистрировать команды — тесты T035 проходят
- [ ] T037 [US6] Навык `.claude/skills/fix-reports/SKILL.md` по contracts/skill-workflow.md (правка через черновик с сохранением id; пояснение правила при отказе; сводка) (FR-042)

---

## Phase 9: Polish & приёмка

- [ ] T038 [P] Команда `quality-sample` в `src/french_learning/agent/quality.py` + тест в `tests/unit/agent/test_quality.py`: Markdown-чек-лист пунктов без `needs_review` (урок, упражнение, пункт, текст с подставленным ответом, путь исходника), итог «пунктов для сверки: N, допустимо ошибок: ⌊0.05·N⌋» (SC-005)
- [ ] T039 [P] `CLAUDE.md`: навыки `/add-lesson`, `/add-material`, `/fix-reports` и новые команды в разделе «Команды»; `README.md`; `CHANGELOG.md`
- [ ] T040 Полный прогон: `ruff check`, `ruff format --check`, `check_no_content.py`, `pytest`
- [ ] T041 Подготовить настоящее хранилище: `init-content C:/Users/Kate/source/french_learning_materials`, переключить `.env` (`CONTENT_DIR`, `SOURCE_MATERIALS_DIR`), первая отправка на GitHub
- [ ] T042 Приёмка с пользователем по quickstart.md на уроках 13 и 14 (шаги 1–12), исправление инструкций навыков по результатам
- [ ] T043 Замер SC-005 (`quality-sample`, сверка пользователем); если ошибок > 5% — доработать `content-rules.md` и повторить на одном уроке
- [ ] T044 После приёмки: статус 002 в `docs/roadmap.md` → ✅, `CHANGELOG.md`, слияние ветки в `main` при проходящих тестах и отправка

---

## Dependencies & Execution Order

- Setup → Foundational (блокирует всё) → US1 (MVP) → US2 → US3 / US4 (параллельно) →
  US5 / US6 (параллельно) → Polish
- US1 T024 зависит от T022, T023; T025 — от всех команд US1
- Команды: тест → убедиться, что падает → реализация → тест проходит

### Parallel Opportunities

- Setup: T002, T003
- Foundational: тесты T004, T006, T008, T010, T012, T014
- US1: тесты T016, T017, T018

## Implementation Strategy

1. Setup + Foundational → US1 → **остановка**: пользователь запускает `/add-lesson` на уроке 14
   (настоящие материалы) — первое реальное использование
2. US2 → повтор на уроке 13
3. US3–US6 → Polish → приёмка по quickstart и SC-005 → слияние
