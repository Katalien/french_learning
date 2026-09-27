# Формат контента (версия 1)

Действующее описание формата хранилища `french_learning_materials`. На него опираются
приложение (функция 001) и навыки агента (функция 002). Схема в коде:
`src/french_learning/content/schema.py`. История: создан в `specs/001-…/contracts/`,
дополнен в функции 002 (журнал файлов, поле `resolved`, черновик `.staging/`).

Договор между агентом (пишет контент, функция 002) и приложением (читает и показывает).
Схема реализуется моделями в `src/french_learning/content/schema.py`; команда
`uv run french-learning validate-content` проверяет хранилище по этой схеме и должна
вызываться агентом перед каждым сохранением. Изменение формата — только через
спецификацию с повышением `format_version` и переводом существующего контента.

## Структура хранилища (`french_learning_materials/`)

```text
format.yaml                 # format_version: 1
topics.yaml                 # справочник разделов и тем
lessons/
  014/
    lesson.yaml             # урок
    theory/th-xxxxxxxx.md   # теория (Markdown + YAML-шапка)
    texts/tx-xxxxxxxx.md    # тексты
    exercises/ex-xxxxxxxx.yaml
    sources/                # сжатые копии исходников (jpg, pdf, docx)
    inventory.md            # опись урока (функция 002, для человека)
extra/                      # элементы без урока (те же подпапки theory/texts/exercises/sources)
vocabulary/voc-xxxxxxxx.yaml
reports/rep-xxxxxxxx.yaml
index.md                    # общий указатель (функция 002, для человека)
```

Папка урока — номер с нулями до трёх знаков. Файлы, не описанные здесь, приложение
игнорирует.

## `format.yaml`

```yaml
format_version: 1
```

## `topics.yaml`

```yaml
sections:
  - {id: grammar, name: Грамматика}
  - {id: vocabulary, name: Лексика}
  - {id: pronunciation, name: Произношение}
topics:
  - {id: top-4f7k2m3a, name: Партитивные артикли, section: grammar}
  - {id: top-9d2j6c5b, name: Il y a / il n'y a pas, section: grammar}
```

## `lessons/NNN/lesson.yaml`

```yaml
id: les-3h8k2m4n
number: 14
date: 2026-09-20          # необязательно
source_folder: Leçon 14
media:
  - {name: Video.mov, type: video, part: class, path: Leçon 14/Video.mov}
```

## Теория и тексты (`.md`)

```markdown
---
id: th-6n2p8q4r
kind: theory              # или text
title: Частичные артикли
lesson: 13                # нет → элемент без урока
part: class
topics: [top-4f7k2m3a]
origin: material
sources:
  - {file: lessons/013/sources/chastichnye-artikli.pdf, original: Частичные артикли .pdf}
needs_review: {flag: false}
---
## Формы
| | Мужской род | Женский род |
|---|---|---|
| ед. ч. | du, de l' | de la, de l' |

Il mange **du** poulet. — *Он ест курицу.*
```

Изображения внутри теории — `![подпись](sources/имя.jpg)`, путь относительно папки урока.

## Упражнение (`exercises/ex-….yaml`)

```yaml
id: ex-7kq2m9pd
kind: exercise
type: gap_choice
lesson: 14
part: homework
number: 4
sheet_number: "1"
topics: [top-4f7k2m3a]
description_ru: Вставить партитивный артикль
instruction:
  ru: Вставьте du, de la, de l' или des.
  original: Complétez avec « du », « de la », « de l' » ou « des ».
  original_lang: fr
  origin: ai              # перевод формулировки
status: main
reference: |              # необязательно; скрыта по умолчанию
  | du | de la | de l' | des |
links: {text: null, theory: th-6n2p8q4r}
show_source: false
origin: material
answers_origin: ai
sources:
  - {file: lessons/014/sources/img_3766.jpg, original: IMG_3766.jpeg}
needs_review: {flag: false}
options: [du, de la, de l', des]
items:
  - id: 1
    text: Je mange {{1}} pain le matin.
    answers: {1: [du]}
  - id: 2
    text: Elle boit {{1}} eau fraîche.
    answers: {1: [de l']}
    needs_review: {flag: true, note: "Буква на фото плохо читается: «fraîche» или «fraiche»"}
```

Поля пунктов по типам — [data-model.md](../data-model.md#типы-упражнений-и-пункты).
Для `grouping` у упражнения есть `groups: [..]`; для `choice` варианты — в пункте.

## Лексика (`vocabulary/voc-….yaml`)

```yaml
id: voc-2m5k8p3q
kind: vocab
entry_type: word
text: maison
article: la
gender: f
flags: {plural_only: false, h_aspire: false}
pos: nom
translations:
  - {text: дом, lesson: 14, origin: material}
lessons: [14]
topics: [top-1a2b3c4d]
origin: material
sources: [{file: lessons/014/sources/lexique.jpg, original: IMG_3490.jpeg}]
needs_review: {flag: false}
```

## Сообщение об ошибке (`reports/rep-….yaml`)

```yaml
id: rep-5t7y2u9i
element: ex-7kq2m9pd
item: 2
comment: Должно быть «de l'», а не «de la».
created: 2026-09-27T18:40:00
status: open              # open | fixed | rejected
resolution: null          # заполняет агент
```

## Правила проверки (выполняет приложение и `validate-content`)

1. `format.yaml` существует, версия поддерживается.
2. Каждый файл соответствует схеме своего вида; ошибка одного файла не мешает остальным.
3. Идентификаторы уникальны во всём хранилище.
4. Все ссылки (`topics`, `links`, `element` в сообщениях) указывают на существующие объекты.
5. Номер упражнения уникален в паре (урок, часть); номер урока уникален.
6. Все пути `sources[].file` существуют внутри хранилища. Нарушение — **предупреждение**:
   элемент загружается и показывается («оригинал недоступен»), но `validate-content`
   сообщает о нём (spec, Edge Cases).
7. Правила типов упражнений (data-model) соблюдены.
8. `needs_review.note` задан при `flag: true`.

`validate-content` печатает список нарушений (файл, поле, сообщение) и завершается с кодом
0 — всё верно, 1 — есть нарушения.

## Дополнения функции 002

### Журнал файлов урока — поле `files` в `lesson.yaml` (необязательное)

```yaml
files:
  - path: Leçon 14/Devoirs/IMG_3874.jpeg   # относительно папки исходных материалов
    part: homework
    sha256: 3f9a…                          # 64 шестнадцатеричных символа
    classification: exercises            # theory | vocabulary | text | exercises |
                                         # exercises_with_reference | media | duplicate |
                                         # unrecognized | skipped
    elements: [ex-7kq2m9pd, ex-2p4r6t8v]
    stored_as: lessons/014/sources/img-3874-3f9a.jpg
  - path: Leçon 14/Video.mov
    part: class
    sha256: …
    classification: media
    elements: []
  - path: Leçon 14/IMG_4191.jpeg
    part: class
    sha256: …
    classification: duplicate
    elements: []
    note: дубль файла Devoirs/IMG_4191.jpeg
```

Правила: `path` уникален в уроке; все `elements` существуют; для `duplicate`,
`unrecognized`, `skipped` обязателен `note`.

### Сообщение об ошибке — поле `resolved`

Дата-время закрытия сообщения агентом (`status: fixed | rejected`, `resolution` обязателен).

### Черновик `.staging/`

`CONTENT_DIR/.staging/<операция>/` — та же структура, что у хранилища; применяется командой
`commit-staging` целиком или не применяется. Удаления — `_delete.txt` (пути относительно
хранилища, по одному в строке). Папка `.staging/` исключена из git хранилища.

### Опись урока и указатель

`lessons/NNN/inventory.md` и `index.md` генерируются командой `build-archive`
(вызывается `commit-staging` автоматически). Руками не править.

## Дополнения функции 003

- У лексики необязательные поля `hidden: true` (запись из урока скрыта пользователем)
  и `completed_by_ai: [gender, article, forms, verb, pos]` (какие поля заполнил агент).
- Прогресс повторения — `.progress/progress.sqlite` (не в git), резервная копия —
  `backups/progress.sql` (в git, коммитится раз в день и по кнопке).
