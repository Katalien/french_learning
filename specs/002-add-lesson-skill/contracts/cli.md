# Contract: вспомогательные команды для навыков

Вызываются агентом как `uv run french-learning <команда>`. Хранилище — `CONTENT_DIR`
из `.env` (или `--content-dir`). Машинный вывод — JSON в stdout (UTF-8), сообщения
для человека — stderr. Коды выхода: `0` — успех, `1` — нарушения / отказ по данным,
`2` — неверные аргументы или окружение.

Все пишущие команды отказываются работать (код 2), если `CONTENT_DIR` лежит внутри
репозитория кода или не является отдельным git-репозиторием (research R12).

| Команда | Что делает | Вывод |
|---|---|---|
| `init-content <папка>` | Создаёт пустое хранилище: `format.yaml`, `topics.yaml` с разделами, `.gitignore` (`.staging/`), первый коммит | текст |
| `scan-lesson <папка урока> [--materials-root <корень>]` | Опись файлов папки и `Devoirs`: путь, часть, размер, тип (image / pdf / docx / audio / video / other), SHA-256, дата (EXIF или mtime), дубли по хешу, состояние относительно журнала урока (`new` / `processed` / `changed` / `missing`), номер урока из имени папки, предлагаемая дата | JSON `{lesson, suggested_date, files:[…]}` |
| `store-source <файл> --lesson N` | Сжатая копия исходника в `.staging/<op>/lessons/NNN/sources/`; возвращает путь для `sources[].file` | JSON `{stored_as}` |
| `new-ids <префикс> [--count K]` | Новые уникальные идентификаторы (проверка против хранилища и черновика) | JSON `[…]` |
| `vocab-find <текст> [--pos P] [--gender G]` | Кандидаты в словаре: точные и похожие (без учёта регистра и диакритики) | JSON `[{id, text, article, gender, pos, translations, lessons, exact}]` |
| `topics-list` | Справочник тем с разделами и числом элементов | JSON |
| `next-number --lesson N --part class|homework` | Следующий сквозной номер упражнения во вкладке (с учётом черновика) | JSON `{number}` |
| `stage-check [--op <id>]` | Проверка «хранилище + черновик» схемой 001 без применения | JSON `{ok, errors:[{path, message}]}` |
| `commit-staging --op <id> -m "<сообщение>"` | Проверка → атомарное применение → `build-archive` → git-коммит → отправка → удаление черновика | JSON `{applied, committed, pushed, warning, files}` |
| `build-archive [--lesson N]` | Перестраивает `inventory.md` урока(ов) и `index.md` | текст |
| `reports-list [--status open]` | Сообщения об ошибках с путями элемента и его исходников | JSON |
| `report-resolve <rep-id> fixed|rejected --resolution "<текст>"` | Закрывает сообщение (коммит + отправка) | JSON `{committed, pushed, warning}` |
| `quality-sample --lesson N [--lesson M]` | Чек-лист пунктов упражнений без «требует проверки» для ручной сверки (SC-005) | Markdown |
| `validate-content` | (из 001) проверка хранилища | текст |
