"""Команды для навыков агента (specs/002-add-lesson-skill/contracts/cli.md).

Машинный вывод — JSON в stdout (UTF-8), сообщения для человека — stderr.
Коды выхода: 0 — успех, 1 — нарушения в данных, 2 — неверные аргументы или окружение.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from french_learning.config import Settings


class UsageError(Exception):
    """Неверные аргументы или окружение (код выхода 2)."""


def emit(data) -> None:
    def default(obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return str(obj)

    print(json.dumps(data, ensure_ascii=False, indent=2, default=default))


def fail(message: str, code: int = 2) -> int:
    print(message, file=sys.stderr)
    return code


def _content_dir(args: argparse.Namespace) -> Path | None:
    if getattr(args, "content_dir", None):
        return Path(args.content_dir)
    return Settings().content_dir


def _readable(args: argparse.Namespace) -> Path:
    root = _content_dir(args)
    if root is None or not root.is_dir():
        raise UsageError("хранилище не найдено: укажите --content-dir или CONTENT_DIR в .env")
    return root


def _writable(args: argparse.Namespace) -> Path:
    from french_learning.agent.storage import StorageError, ensure_writable_storage

    try:
        return ensure_writable_storage(_content_dir(args))
    except StorageError as exc:
        raise UsageError(str(exc)) from exc


def _init_content(args) -> int:
    from french_learning.agent.storage import StorageError, init_content

    try:
        init_content(Path(args.folder))
    except StorageError as exc:
        return fail(str(exc))
    print(f"Хранилище создано: {args.folder}", file=sys.stderr)
    return 0


def _new_ids(args) -> int:
    from french_learning.agent.ids import new_ids

    emit(new_ids(_readable(args), args.prefix, args.count))
    return 0


def _stage_check(args) -> int:
    from french_learning.agent.staging import stage_check

    result = stage_check(_readable(args), args.op)
    emit({"ok": result.ok, "errors": [dataclasses.asdict(e) for e in result.errors]})
    return 0 if result.ok else 1


def _commit_staging(args) -> int:
    from french_learning.agent.staging import StagingError, commit_staging

    try:
        result = commit_staging(_writable(args), args.op, args.message)
    except StagingError as exc:
        return fail(str(exc), 1)
    emit(result)
    return 0 if result.applied else 1


def _build_archive(args) -> int:
    from french_learning.agent.archive import build_archive

    changed = build_archive(_writable(args))
    print(f"Обновлено файлов: {len(changed)}", file=sys.stderr)
    return 0


def _scan_lesson(args) -> int:
    from french_learning.agent.scan import ScanError, scan_lesson

    folder = Path(args.folder)
    if args.materials_root:
        materials = Path(args.materials_root)
    else:
        materials = Settings().source_materials_dir or folder.parent
    root = _content_dir(args)
    try:
        result = scan_lesson(folder, materials, root if root and root.is_dir() else None)
    except ScanError as exc:
        return fail(str(exc))
    emit(result)
    return 0


def _store_source(args) -> int:
    from french_learning.agent.sources import store_source

    source = Path(args.file)
    if not source.is_file():
        return fail(f"файл не найден: {source}")
    emit({"stored_as": store_source(source, args.lesson, _writable(args), args.op)})
    return 0


def _next_number(args) -> int:
    from french_learning.agent.numbers import next_number

    emit({"number": next_number(_readable(args), args.lesson, args.part, args.op)})
    return 0


def _topics_list(args) -> int:
    from french_learning.agent.numbers import topics_list

    emit(topics_list(_readable(args)))
    return 0


def _vocab_find(args) -> int:
    from french_learning.agent.vocab import vocab_find

    emit(vocab_find(_readable(args), args.text, pos=args.pos, gender=args.gender))
    return 0


def _reports_list(args) -> int:
    from french_learning.agent.reports import reports_list

    emit(reports_list(_readable(args), status=args.status or None))
    return 0


def _report_resolve(args) -> int:
    from french_learning.agent.reports import ReportError, report_resolve

    try:
        result = report_resolve(_writable(args), args.report, args.status, args.resolution)
    except ReportError as exc:
        return fail(str(exc))
    emit(result)
    return 0


def _quality_sample(args) -> int:
    from french_learning.agent.quality import quality_sample

    print(quality_sample(_readable(args), args.lesson))
    return 0


def _restore_progress(args) -> int:
    from french_learning.practice.backup import BACKUP_PATH, restore

    root = _readable(args)
    source = Path(args.source) if args.source else root / BACKUP_PATH
    if not source.is_file():
        return fail(f"копия не найдена: {source}")
    database = restore(root, source)
    print(f"Прогресс восстановлен из {source} в {database} (прежний файл — .bak)", file=sys.stderr)
    return 0


def _trainers_list(args) -> int:
    from french_learning.agent.trainers import trainers_list

    emit(trainers_list(_readable(args)))
    return 0


def _trainer_context(args) -> int:
    from french_learning.agent.trainers import TrainerNotFound, trainer_context

    try:
        emit(trainer_context(_readable(args), args.trainer))
    except TrainerNotFound as exc:
        return fail(str(exc))
    return 0


def _mistakes_list(args) -> int:
    from french_learning.agent.trainers import mistakes_list

    emit(mistakes_list(_readable(args), args.trainer, args.lesson))
    return 0


def register(commands) -> None:
    """Добавить команды агента в парсер `french-learning`."""

    def add(name, handler, help_text, content=True):
        parser = commands.add_parser(name, help=help_text)
        if content:
            parser.add_argument("--content-dir", help="папка хранилища (иначе CONTENT_DIR)")
        parser.set_defaults(handler=handler)
        return parser

    p = add("init-content", _init_content, "создать пустое хранилище контента", content=False)
    p.add_argument("folder")

    p = add("new-ids", _new_ids, "новые уникальные идентификаторы")
    p.add_argument("prefix", choices=["les", "th", "tx", "ex", "voc", "top", "rep", "tb"])
    p.add_argument("--count", type=int, default=1)

    p = add("stage-check", _stage_check, "проверить черновик вместе с хранилищем")
    p.add_argument("--op", default="current")

    p = add("commit-staging", _commit_staging, "применить черновик: коммит и отправка")
    p.add_argument("--op", default="current")
    p.add_argument("-m", "--message", required=True)

    add("build-archive", _build_archive, "перестроить опись уроков и указатель")

    p = add("scan-lesson", _scan_lesson, "опись папки урока")
    p.add_argument("folder")
    p.add_argument("--materials-root", help="корень исходных материалов (SOURCE_MATERIALS_DIR)")

    p = add("store-source", _store_source, "сжатая копия исходника в черновик")
    p.add_argument("file")
    p.add_argument("--lesson", type=int)
    p.add_argument("--op", default="current")

    p = add("next-number", _next_number, "следующий номер упражнения во вкладке")
    p.add_argument("--lesson", type=int, required=True)
    p.add_argument("--part", choices=["class", "homework"], required=True)
    p.add_argument("--op", default="current")

    add("topics-list", _topics_list, "справочник тем")

    p = add("vocab-find", _vocab_find, "поиск слова в словаре")
    p.add_argument("text")
    p.add_argument("--pos")
    p.add_argument("--gender", choices=["m", "f", "both"])

    p = add("reports-list", _reports_list, "сообщения об ошибках")
    p.add_argument("--status", default="open", help="open, fixed, rejected; пусто — все")

    p = add("report-resolve", _report_resolve, "закрыть сообщение об ошибке")
    p.add_argument("report")
    p.add_argument("status", choices=["fixed", "rejected"])
    p.add_argument("--resolution", required=True)

    p = add("restore-progress", _restore_progress, "восстановить прогресс из резервной копии")
    p.add_argument("--source", help="файл SQL-дампа (по умолчанию backups/progress.sql)")

    p = add("quality-sample", _quality_sample, "чек-лист для сверки качества (SC-005)")
    p.add_argument("--lesson", type=int, action="append", required=True)

    add("trainers-list", _trainers_list, "каталог тренажёров и заданий в пулах")

    p = add("trainer-context", _trainer_context, "всё для генерации заданий тренажёра")
    p.add_argument("trainer")

    p = add("mistakes-list", _mistakes_list, "ошибки в тренажёре и в упражнениях уроков")
    p.add_argument("--trainer")
    p.add_argument("--lesson", type=int)
