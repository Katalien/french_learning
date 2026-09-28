# French Learning

Личное веб-приложение для изучения французского языка: база знаний по урокам, словарь
с карточками и интерактивные упражнения. Материалы уроков (фото, PDF, документы)
превращает в структурированный контент агент Claude Code.

Учебный контент и личные данные хранятся в отдельном приватном репозитории и в этот
(публичный) репозиторий не попадают.

## Требования

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Установка

```bash
uv sync
uv run pre-commit install
uv run french-learning tts-download
```

Последняя команда один раз скачивает голоса озвучки Piper (около 130 МБ, в
`~/.french-learning/tts`); после этого произношение работает без интернета.

Скопируйте `.env.example` в `.env` и укажите путь к хранилищу контента:

```
CONTENT_DIR=C:/путь/к/french_learning_materials
SOURCE_MATERIALS_DIR=C:/путь/к/исходным/материалам
```

## Запуск

```bash
uv run french-learning serve
```

Приложение откроется по адресу http://127.0.0.1:8000 (доступно только с этого компьютера).

### Ярлык на рабочем столе (Windows)

```bash
powershell -ExecutionPolicy Bypass -File scripts/windows/make-shortcuts.ps1
```

Создаёт ярлыки «French Learning» (запускает сервер в фоне, если он ещё не работает, и открывает
приложение в браузере) и «French Learning — остановить». Журнал сервера —
`%LOCALAPPDATA%\french-learning\server.log`. Иконка — `scripts/make_icon.py`.

## Словарь и повторение

Вкладка «Словарь»: просмотр слов, добавление по одному и списком, повторение карточек
(алгоритм FSRS). Прогресс хранится в хранилище контента в `.progress/` и раз в день
копируется в `backups/progress.sql` (коммит и отправка на GitHub). Восстановить:

```bash
uv run french-learning restore-progress
```

## Проверка контента

```bash
uv run french-learning validate-content
```

## Демо без настоящих материалов

```bash
uv run french-learning demo-init C:/путь/к/french_learning_demo
```

Затем укажите эту папку в `CONTENT_DIR`.

## Разработка

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Перед коммитом и отправкой git-хуки автоматически запускают линтер, проверку на отсутствие
учебных материалов в репозитории и тесты.

## Документация проекта

- [Конституция](.specify/memory/constitution.md) — правила проекта
- [Дорожная карта](docs/roadmap.md) — функции и порядок работ
- [Спецификации](specs/) — требования, планы и задачи функций
