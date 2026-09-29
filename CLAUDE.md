# French Learning

Личное веб-приложение для изучения французского: база знаний по урокам, словарь с
карточками и интерактивные упражнения. Материалы уроков (фото, PDF, документы) превращает
в структурированный контент агент Claude Code.

## Общение

- Отвечай на русском.
- Пользователь — заказчик: ставит условия, обсуждает, принимает результат. Код пишет Claude.
- Пользователь новичок в Spec Kit и разработке с агентом — объясняй решения и шаги.

## Где что лежит

- `.specify/memory/constitution.md` — конституция: правила проекта, соблюдать обязательно.
- `docs/roadmap.md` — дорожная карта: функции, порядок, пожелания к спецификациям.
- `specs/NNN-*/` — спецификации, планы и задачи функций (Spec Kit).
- Контент и данные прогресса — приватный репозиторий `Katalien/french_learning_materials`,
  локально `C:\Users\Kate\source\french_learning_materials` (путь задаётся настройкой).
- Исходные материалы преподавателя — `C:\Users\Kate\Documents\french_learning_materials`
  (только чтение, вне обоих репозиториев).

## Стек

Python 3.12 + uv, FastAPI, серверные шаблоны + HTMX + Alpine.js (локально, без сборки),
SQLite для прогресса, pytest, ruff. Подробнее — конституция, раздел Constraints.

Оформление (009) — своя система на CSS-переменных, без CSS-библиотек:
`web/static/css/tokens.css` (палитра «Перелив», светлая / тёмная тема, шрифты),
`base.css`, `components.css`, `screens.css`; шрифты Inter и Lora лежат в `web/static/fonts/`.
Выбор дизайна и макеты — `specs/009-redesign/design.md`, `mockups/final.html`.

Заметки (005) — пакет `notes/` (`store.py` — хранение и правила, `grouping.py` — страница
«Заметки к уроку»), таблица `notes` в базе прогресса (схема v3), JSON API `web/routes/notes.py`.
В браузере — `static/js/selection.js` (подсказка у выделения с секциями; 006 добавит перевод)
и `static/js/notes.js` (отметки фрагментов по цитате с контекстом, поле, окна). Разметка
заметки в `notes.js` и `partials/note_item.html` должна совпадать.

Перевод при выделении (006) — пакет `translate/` (`normalize.py` — ключ и проверки,
`providers.py` — MyMemory / DeepL через `urllib`, `lemma.py` — начальная форма simplemma и вид
записи, `cache.py` — запас `translations` в базе прогресса (схема v4), `service.py` — порядок
«словарь → запас → сервис»), маршруты `web/routes/translate.py` (`/translate`,
`/vocab/from-text`, настройки). В браузере — секция `static/js/translate.js` в общей подсказке
`selection.js`; зоны перевода — `[data-note-container]`, `[data-translate]`, `[lang="fr"]`.
Ключ DeepL — только `DEEPL_API_KEY` в `.env` (не в базе: база уходит в резервную копию).
Во внешний сервис уходит только выделенное и его начальная форма; в тестах сеть подменяется.

## Критичные правила

- НИКОГДА не коммить материалы уроков, распознанный контент и личные данные в этот
  репозиторий — он публичный.
- Всё созданное ИИ или внешним сервисом помечается происхождением (конституция, принцип I).
- Не коммитить и не пушить при падающих тестах; не обходить проверки (`--no-verify` и т. п.).
- Секреты (ключи API, пароли) никогда не коммитить.
- Новые функции — только через цикл Spec Kit: specify → clarify → plan → tasks → analyze →
  implement. Ветка функции — `NNN-название`.

## Команды

- `uv sync` — установить зависимости; `uv run pre-commit install` — git-хуки.
- `uv run french-learning serve` — запустить приложение (http://127.0.0.1:8000). Пользователь
  запускает его ярлыком «French Learning» на рабочем столе (`scripts/windows/`: сервер в фоне,
  журнал в `%LOCALAPPDATA%\french-learning`); перед `uv sync` фоновый сервер надо остановить
  (ярлык «остановить» или `scripts/windows/stop-app.ps1`). Скрипты .ps1 — в UTF-8 с BOM
  (иначе Windows PowerShell 5.1 ломает русский текст).
- `uv run french-learning validate-content` — проверить хранилище контента (вызывать перед
  сохранением контента агентом).
- `uv run french-learning tts-download` — скачать голоса озвучки Piper (около 130 МБ, один раз;
  хранятся в `~/.french-learning/tts`, там же кеш звука).
- `uv run french-learning demo-init <папка> [--with-broken]` — демо-хранилище с придуманными
  уроками.
- `uv run pytest` — тесты; `uv run ruff check .` и `uv run ruff format .` — линтер и форматтер.
- `uv run python scripts/check_no_content.py` — проверка, что в репозитории нет материалов.
- Команды для навыков агента (`scan-lesson`, `store-source`, `new-ids`, `next-number`,
  `topics-list`, `vocab-find`, `stage-check`, `commit-staging`, `build-archive`,
  `reports-list`, `report-resolve`, `quality-sample`, `init-content`, `restore-progress`) —
  `specs/002-add-lesson-skill/contracts/cli.md`; для тренажёров (`trainers-list`,
  `trainer-context`, `mistakes-list`) — `specs/004-exercises-trainers/contracts/cli.md`.
- `uv run french-learning serve --port 8010 --content-dir <демо>` — второй экземпляр на
  демо-хранилище (для проверок, не трогает настоящий прогресс).

## Навыки агента

- `/add-lesson <папка или «урок N»>` — добавить урок, дописать домашку, переклассифицировать файл.
- `/add-material <ссылка>` — материал из интернета в «Дополнительные материалы».
- `/fix-reports` — разобрать сообщения об ошибках из приложения.
- `/complete-words` — дополнить слова словаря с пометкой «нужно дополнить» (род, формы, спряжение).
- `/generate-tasks <тренажёр> [N]` — пакет заданий для тренажёра (только по просьбе).
- `/add-trainer <описание>` — новый тренажёр в каталоге `trainers.yaml`.
- `/explain-mistakes [тренажёр | урок N]` — разбор ошибок в чате.
- Общие правила разбора — `.claude/skills/_shared/content-rules.md`; формат контента —
  `docs/content-format.md`. Контент пишется только через черновик и `commit-staging`.

## Прогресс повторения

- База прогресса (карточки, оценки, сеансы, настройки) — `CONTENT_DIR/.progress/progress.sqlite`
  (не в git). Резервная копия — `backups/progress.sql` в хранилище: коммит и отправка раз в день
  при работающем приложении и по кнопке; восстановление — `french-learning restore-progress`.
- Проверка введённых ответов — `src/french_learning/practice/checking.py` (общая для словаря
  и упражнений); проверка упражнений по типам — `exercises/grading.py`.
- Попытки упражнений (черновик, итог первой проверки, «исправлено» / «подсмотрен») —
  `exercises/attempts.py`; ответы тренажёров и их расписание FSRS — `trainers/schedule.py`.
  Всё в той же базе прогресса и её резервной копии.
