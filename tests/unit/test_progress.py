"""Интерфейс прогресса: в функции 001 выполненных заданий нет (появятся в 004)."""

from french_learning.content.progress import NoProgress


def test_nothing_done_yet():
    progress = NoProgress()
    assert progress.is_done("ex-anything") is False
