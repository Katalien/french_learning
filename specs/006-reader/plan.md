# Implementation Plan: Чтение с переводом

**Branch**: `006-reader` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-reader/spec.md`; макет —
[mockups/index.html](mockups/index.html); общая подсказка выделения — из 005
(`static/js/selection.js`).

## Summary

Выделение французского текста в любом месте приложения показывает в подсказке:
- перевод;
- начальную форму слова;
- 🔊;
- «+ В словарь».

Под ними остаётся полоска «пометка · вопрос» из 005.

Откуда берётся перевод, по порядку:
1. словарь пользователя;
2. запас уже полученных переводов (новая таблица в базе прогресса);
3. внешний сервис — MyMemory без ключа или DeepL с ключом из `.env`.

Начальная форма определяется локально библиотекой simplemma. «+ В словарь» одним нажатием
создаёт запись:
- с переводом (происхождение «внешний сервис»);
- с предложением-примером и уроком;
- без темы.

Переключатель «Перевод при выделении» — в меню «⋯».

## Technical Context

**Language/Version**: Python 3.12 (uv)

**Primary Dependencies**: + **simplemma 2.0** (MIT, 19 МБ, без сети) — скачивание с согласия
пользователя. HTTP к сервисам — стандартный `urllib`, новых сетевых библиотек нет

**Storage**:
- база прогресса, схема 3 → 4 (таблица `translations`, настройки `translator`,
  `mymemory_email`);
- ключ DeepL — `DEEPL_API_KEY` в `.env`;
- cookie `translate`;
- запись словаря — через `VocabEditor` (контент, коммит)

**Testing**: pytest, TDD для:
- нормализации;
- порядка «словарь → запас → сервис», запаса без дублей и без записи ошибок;
- разбора ответов MyMemory и DeepL (сервисы подменяются в тестах, настоящих запросов
  в тестах нет);
- начальной формы и вида записи;
- признака «абзац»;
- `add_word` с примером и происхождением, без `lessons`, без дублей;
- маршрутов `/translate`, `/vocab/from-text` и настроек;
- миграции v4;
- разметки: зоны, переключатель.

JS — по quickstart

**Target Platform**: браузер компьютера; телефон — вёрстка 375 px

**Performance Goals**: словарь или запас — ответ `/translate` < 100 мс (SC-001: подсказка
< 0,3 с); сервис — тайм-аут 5 с

**Constraints**:
- во внешний сервис уходит только выделенное (IX);
- без сети всё работает, перевод — из запаса или «недоступен»;
- ключ не попадает в копию и репозитории

**Scale/Scope**:
- пакет `translate/` (~4 модуля);
- 5 маршрутов;
- 1 JS-модуль и правки `selection.js`;
- `data-translate` в ~8 шаблонах;
- ~40 тестов

## Constitution Check

| Принцип | Как соблюдается | Статус |
|---|---|---|
| I. Прослеживаемость | Перевод от сервиса в словаре — `origin: service`; видно при «Происхождение: везде»; в подсказке пометки нет (разрешено: «не мешать чтению») | ✅ |
| II. Пользователь управляет контентом | Добавление в словарь только по кнопке; правка и удаление — как у своих слов (003) | ✅ |
| VI. Разделение данных | Запас переводов — в базе прогресса; ключ — только `.env`; контент — приватное хранилище | ✅ |
| IX. Без внешних сервисов для ядра | Перевод — дополнительная функция; без сети — «недоступен», остальное работает; наружу — только выделенное | ✅ |
| X. Экономия ИИ | ИИ не используется; начальная форма — локальная библиотека | ✅ |
| XI. Простота | Один интерфейс сервиса с двумя реализациями; `urllib` вместо новой библиотеки; общая подсказка 005 | ✅ |
| XII. Только локально | Новые адреса на 127.0.0.1 | ✅ |
| XIII. TDD | Логика перевода, запаса, форм и добавления — тесты до кода | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/006-reader/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/translate-api.md · contracts/ui-routes.md
├── mockups/index.html
└── tasks.md
```

### Source Code (repository root)

```text
src/french_learning/
├── translate/                  # новый пакет
│   ├── __init__.py
│   ├── normalize.py            # нормализация ключа, кириллица, «абзац»
│   ├── providers.py            # Translator: MyMemory, DeepL (urllib, тайм-аут 5 с)
│   ├── cache.py                # запас translations
│   ├── lemma.py                # simplemma: начальная форма, вид записи
│   └── service.py              # словарь → запас → сервис; результат для /translate
├── practice/db.py              # SCHEMA_VERSION = 4, translations, настройки
├── config.py                   # deepl_api_key
├── vocab/edits.py              # add_word: example, translation_origin
├── web/routes/translate.py     # /translate, /vocab/from-text, /settings/translate…
├── web/static/js/selection.js  # зоны перевода, ctx.zone / ctx.noteContainer, ✕
├── web/static/js/translate.js  # секция перевода (новый)
├── web/static/js/notes.js      # секция 005 — по ctx.noteContainer
└── web/templates/              # base (⋯, data-translate), vocab/settings, data-translate в шаблонах
tests/
├── unit/translate/test_normalize.py · test_service.py · test_providers.py · test_lemma.py
├── unit/vocab/test_edits.py    # + пример, происхождение
├── unit/practice/test_db.py    # + схема 4
└── integration/test_translate.py
```

**Structure Decision**: перевод — отдельный пакет `translate/`, как `notes/`. Сервисы
подключаются через общий интерфейс. Подсказка остаётся одной на всё приложение
(`selection.js`), 006 добавляет в неё секцию.

## Complexity Tracking

Новая зависимость — simplemma (19 МБ). Обоснование: FR-010 требует локальную начальную
форму, это самая лёгкая библиотека с французским. Без неё пришлось бы или отказаться
от начальной формы, или ставить spaCy (сотни МБ).

## Constitution Check — после Phase 1

Все пункты ✅. Замечание: почта для MyMemory — личные данные. По умолчанию она не передаётся;
в настройках рядом с полем — пояснение, что почта уйдёт в сервис перевода.
