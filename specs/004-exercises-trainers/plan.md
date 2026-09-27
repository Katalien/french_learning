# Implementation Plan: Упражнения с автопроверкой и тренажёры

**Branch**: `004-exercises-trainers` | **Date**: 2026-09-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-exercises-trainers/spec.md`

## Summary

Упражнения уроков становятся интерактивными формами. Проверка всего упражнения идёт
на сервере по правилам конституции VIII: общий модуль `checking.py` из 003, выбор написания,
«Показать ответ», исправление. Каждая проверка — попытка в SQLite: итог первой проверки
и отметки «исправлено самостоятельно» / «подсмотрен ответ». Есть черновик, «Решить заново»,
история с пересчётом после исправлений агента, «Мои ошибки», «Не согласна», смена статуса.
Появляется счётчик домашки.

Тренажёры бывают двух видов:
- **встроенные** — 9 генераторов из словаря, чисел и упражнений уроков, с FSRS
  по каждому вопросу;
- **с заданиями от агента** — пакеты в приватном хранилище, пул / архив / «Ошибки»
  и статистика.

Каталог тренажёров: встроенные описаны в коде, собственные тренажёры и переопределения —
в `trainers.yaml`. Три новых навыка агента: `/generate-tasks`, `/add-trainer`,
`/explain-mistakes`.

## Technical Context

**Language/Version**: Python 3.12 (uv)

**Primary Dependencies**: существующие (FastAPI, Jinja2, HTMX, Alpine.js, pydantic, `fsrs`,
`piper-tts`); новых нет. Запись чисел по-французски — своя функция (R11).

**Storage**: контент — YAML (`trainers.yaml`, `trainers/<id>/tb-*.yaml`, поле `status`
упражнений); прогресс — SQLite, схема v2 (`exercise_attempts`, `trainer_cards`,
`trainer_answers`, `trainer_sessions`); копия — `backups/progress.sql`, как в 003

**Testing**: pytest, TDD. Тесты на проверку по типам, итоги и отметки, пересчёт, «Мои
ошибки», генераторы (артикли — контрольный набор SC-005, числа, притяжательные,
указательные), FSRS-очередь (SC-006), пул и архив, каталог, формат пакетов, команды агента.
Интерфейс — интеграционные тесты маршрутов и ручная проверка по quickstart

**Target Platform**: как в 001–003 (локально, браузер компьютера и телефона)

**Project Type**: расширение веб-приложения + навыки агента

**Performance Goals**: проверка упражнения и следующее задание тренажёра — < 200 мс;
генерация вопросов тренажёра по словарю до 5000 записей — < 500 мс

**Constraints**: без интернета (кроме навыков агента); история попыток и ответов
не удаляется; только локальный доступ; экран 375 px

**Scale/Scope**: сотни упражнений, тысячи попыток и ответов в год; 9 встроенных
тренажёров + собственные

## Constitution Check

| Принцип | Как соблюдается | Статус |
|---|---|---|
| I. Прослеживаемость | Пакеты и записи каталога от агента — `origin: ai`, сомнительные — `needs_review`; у правильного ответа видно происхождение при «Не согласна» | ✅ |
| II. Пользователь управляет контентом | Статус упражнения, «Не согласна», переключение источника тренажёра, генерация только по просьбе | ✅ |
| III. Проверка по исключению | Пункты и задания с `needs_review` помечены при проверке | ✅ |
| IV. Интерактивный интерфейс | Все типы упражнений — формы, а не картинки; «по картинке» — исходник рядом | ✅ |
| V. Единый формат | `trainers.yaml` и пакеты — необязательные дополнения v1 со схемой pydantic, проверяются `validate-content` | ✅ |
| VI. Разделение данных | Пакеты и каталог — приватное хранилище; попытки — SQLite вне git + копия в приватном хранилище | ✅ |
| VII. История | Попытки и ответы не удаляются; пересчёт вычисляется при чтении, данные не меняются | ✅ |
| VIII. Французский | Общий `checking.py`: строго к буквам, диакритике и дефисам; клавиатурные различия не ошибка; оба варианта записи чисел | ✅ |
| IX. Без внешних сервисов | Проверка и встроенные тренажёры локально, без сети | ✅ |
| X. Экономия ИИ | Генерация, новые тренажёры и разбор ошибок — только по явной просьбе; встроенные тренажёры без агента | ✅ |
| XI. Простота | Без новых зависимостей; пакеты переиспользуют модели и шаблоны упражнений; `sqlite3` без ORM | ✅ |
| XII. Только локально | Новые маршруты в том же приложении на 127.0.0.1 | ✅ |
| XIII. TDD | Тесты до кода для всей логики | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/004-exercises-trainers/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/ui-routes.md · contracts/cli.md · contracts/trainers-format.md
└── tasks.md
```

### Source Code (repository root)

```text
src/french_learning/
├── content/
│   ├── schema.py               # + TaskBatch, TrainerEntry, префикс tb
│   ├── loader.py               # + trainers.yaml и trainers/*/tb-*.yaml
│   ├── writer.py               # + set_exercise_status
│   └── progress.py             # NoProgress → протокол; реализация в exercises/
├── practice/
│   ├── db.py                   # схема v2, миграция
│   └── checking.py             # (003) + сравнение вариантов списка, true_false, choice
├── exercises/
│   ├── grading.py              # проверка упражнения / пункта по типам
│   ├── attempts.py             # попытки, черновики, итоги, пересчёт, история
│   └── mistakes.py             # «Мои ошибки»
├── trainers/
│   ├── catalog.py              # встроенные + trainers.yaml
│   ├── questions.py            # модель вопроса
│   ├── generators/             # articles, conjugation, forms, possessives,
│   │                           # demonstratives, agreement, numbers, sentences
│   ├── french_numbers.py       # запись чисел 0–1000
│   ├── schedule.py             # FSRS по вопросам (как vocab/cards.py)
│   ├── pools.py                # пакеты: пул, архив, «Ошибки», статистика
│   └── sessions.py             # подход порциями
├── agent/commands.py           # + trainers-list, trainer-context, mistakes-list
├── web/routes/exercises.py     # выполнение, история, статус, «Мои ошибки»
├── web/routes/trainers.py      # каталог, запуск, сеанс, статистика
└── web/templates/{exercises,trainers}/*.html, static/js/symbols.js

.claude/skills/{generate-tasks,add-trainer,explain-mistakes}/SKILL.md
tests/unit/{exercises,trainers}/, tests/integration/test_exercise_*.py, test_trainers_*.py
```

**Structure Decision**: два новых пакета, `exercises/` и `trainers/`, рядом с `vocab/`.
Проверка ответов и FSRS переиспользуются из `practice/`. Панель символов выносится
из шаблонов 003 в общий `symbols.js`.

## Complexity Tracking

Нарушений нет. Самая сложная часть — 9 генераторов. Они независимы и тестируются по
отдельности; в задачах генераторы разбиты так, что каждый можно принять отдельно.

## Constitution Check — после Phase 1

Все пункты ✅. Отдельно:
- VII: итог «пересчитано» вычисляется при показе, в базе он не хранится (R4);
- V: новые файлы необязательны, хранилище без них остаётся корректным (contracts/trainers-format.md).
