"""Прогресс выполнения упражнений.

В функции 001 выполнения ещё нет: счётчик домашки всегда «0 из N».
Функция 004 заменит `NoProgress` реализацией, читающей попытки из SQLite.
"""

from typing import Protocol


class Progress(Protocol):
    def is_done(self, exercise_id: str) -> bool: ...


class NoProgress:
    def is_done(self, exercise_id: str) -> bool:
        return False
