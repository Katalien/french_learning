"""Разбор сообщений об ошибках (US6, FR-042; research R11)."""

from pathlib import Path

import pytest

from french_learning.agent.reports import ReportError, report_resolve, reports_list
from french_learning.content.loader import load_content
from tests.unit.agent.conftest import commits


def test_list_open_reports_with_paths(store: Path):
    [report] = reports_list(store, status="open")
    assert report["id"] == "rep-openaaaa"
    assert report["element_path"] == "lessons/001/exercises/ex-gapchoic.yaml"
    assert report["sources"] == ["lessons/001/sources/sheet.jpg"]
    assert report["item"] == 2


def test_resolve_fixed(store: Path):
    result = report_resolve(store, "rep-openaaaa", "fixed", "Исправлено: eau → eaux")
    report = load_content(store).reports["rep-openaaaa"]
    assert report.status == "fixed"
    assert report.resolution == "Исправлено: eau → eaux"
    assert report.resolved is not None
    assert result.committed
    assert commits(store)[0].startswith("Сообщение rep-openaaaa")
    assert reports_list(store, status="open") == []


def test_rejected_needs_resolution(store: Path):
    with pytest.raises(ReportError):
        report_resolve(store, "rep-openaaaa", "rejected", "  ")


def test_closed_report_cannot_be_closed_again(store: Path):
    report_resolve(store, "rep-openaaaa", "rejected", "Верно: после être партитив сохраняется")
    with pytest.raises(ReportError, match="уже закрыто"):
        report_resolve(store, "rep-openaaaa", "fixed", "x")
