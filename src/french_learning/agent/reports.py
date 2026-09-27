"""Сообщения об ошибках для навыка `/fix-reports` (US6, FR-042; research R11)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from french_learning.content.loader import load_content
from french_learning.content.writer import ContentWriter, WriteResult


class ReportError(Exception):
    """Сообщение нельзя закрыть; сообщение показывается агенту."""


def reports_list(root: Path, status: str | None = "open") -> list[dict]:
    content = load_content(root)
    result = []
    for report in sorted(content.reports.values(), key=lambda r: r.created):
        if status and report.status != status:
            continue
        element = content.elements.get(report.element)
        result.append(
            {
                "id": report.id,
                "element": report.element,
                "item": report.item,
                "comment": report.comment,
                "created": report.created.isoformat(),
                "status": report.status,
                "element_path": content.element_paths.get(report.element)
                or content.batch_paths.get(report.element),
                "sources": [s.file for s in element.sources if s.file] if element else [],
            }
        )
    return result


def report_resolve(root: Path, report_id: str, status: str, resolution: str) -> WriteResult:
    if status not in {"fixed", "rejected"}:
        raise ReportError("статус закрытия: fixed или rejected")
    if not resolution.strip():
        raise ReportError("нужно пояснение: что исправлено или почему ответ верен")
    content = load_content(root)
    relative = content.report_paths.get(report_id)
    if relative is None:
        raise ReportError(f"сообщение {report_id} не найдено")
    path = root / relative
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("status") != "open":
        raise ReportError(f"сообщение {report_id} уже закрыто ({data.get('status')})")
    data.update(
        status=status,
        resolution=resolution.strip(),
        resolved=dt.datetime.now().replace(microsecond=0).isoformat(),
    )
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n"
    )
    label = "исправлено" if status == "fixed" else "отклонено"
    return ContentWriter(root).commit_paths([relative], f"Сообщение {report_id}: {label}")
