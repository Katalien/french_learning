"""Команды приложения: `serve` — запуск сервера, `validate-content` — проверка хранилища.

`validate-content` вызывает агент перед сохранением контента (функция 002).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from french_learning.config import Settings
from french_learning.content.loader import load_content


def _run_server(app, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


def _serve(args: argparse.Namespace) -> int:
    from french_learning.web.app import create_app

    settings = Settings()
    if args.content_dir:
        settings.content_dir = Path(args.content_dir)
    app = create_app(settings)
    print(f"Приложение: http://{settings.host}:{settings.port}")
    _run_server(app, settings.host, settings.port)
    return 0


def _validate(args: argparse.Namespace) -> int:
    root = Path(args.content_dir) if args.content_dir else Settings().content_dir
    if root is None or not root.is_dir():
        print("Хранилище не найдено: укажите --content-dir или CONTENT_DIR в .env")
        return 2
    content = load_content(root)
    if not content.errors:
        print(f"Нарушений нет. Уроков: {len(content.lessons)}, элементов: {len(content.elements)}.")
        return 0
    print(f"Найдено нарушений: {len(content.errors)}")
    for error in content.errors:
        print(f"  {error.path}: {error.message}")
    return 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="french-learning")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="запустить приложение")
    serve.add_argument("--content-dir", help="папка хранилища (иначе CONTENT_DIR)")
    serve.set_defaults(handler=_serve)

    validate = commands.add_parser("validate-content", help="проверить хранилище контента")
    validate.add_argument("--content-dir", help="папка хранилища (иначе CONTENT_DIR)")
    validate.set_defaults(handler=_validate)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
