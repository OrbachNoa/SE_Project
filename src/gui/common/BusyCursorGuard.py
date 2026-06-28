"""Reference-counted application wait-cursor.

Qt's ``setOverrideCursor`` / ``restoreOverrideCursor`` form a stack, so when
several operations set the busy cursor and finish in a different order (or one
fails before restoring), the cursor can get stuck or restored too early. This
guard keeps a single depth counter: the first acquire sets the wait cursor and
only the last matching release restores it.

Use it as a context manager for a scoped block::

    with BusyCursorGuard():
        do_slow_thing()

or call ``push()`` / ``pop()`` for busy state that spans separate events, such
as a ``set_busy(bool)`` toggle driven by a background worker.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QGuiApplication


class BusyCursorGuard:
    """A nesting-safe wait cursor shared across the whole application."""

    _depth = 0

    @classmethod
    def push(cls) -> None:
        if cls._depth == 0:
            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        cls._depth += 1

    @classmethod
    def pop(cls) -> None:
        if cls._depth == 0:
            return
        cls._depth -= 1
        if cls._depth == 0:
            QGuiApplication.restoreOverrideCursor()

    def __enter__(self) -> "BusyCursorGuard":
        type(self).push()
        return self

    def __exit__(self, *exc_info) -> bool:
        type(self).pop()
        return False
