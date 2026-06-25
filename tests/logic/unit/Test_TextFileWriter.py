"""Unit tests for TextFileWriter's write-failure path.

The writer used to print its own "Error: Unable to write..." line to stderr
before re-raising, duplicating the report that the calling boundary already
produces via ExceptionMapperRegistry. It should now just let the exception
propagate, with no local printing.
"""
import pytest

from src.file_io.writers.TextFileWriter import TextFileWriter
from src.models.ExamSchedule import ExamSchedule


# A directory path can't be opened for writing — open() raises a real OSError
# (PermissionError on Windows, IsADirectoryError on POSIX), giving genuine OS
# failure behavior without monkeypatching builtins.open.


# ===========================================================================
# TC-TFW-001: a write failure (target path is a directory, not a file)
# still propagates — the writer does not swallow it.
# ===========================================================================
def test_write_failure_still_raises(tmp_path):
    with pytest.raises(OSError):
        TextFileWriter().write([ExamSchedule()], str(tmp_path))


# ===========================================================================
# TC-TFW-002: no local stderr print happens on a write failure — the
# boundary that maps every export error is the only one that reports it.
# ===========================================================================
def test_write_failure_does_not_print_to_stderr(capsys, tmp_path):
    with pytest.raises(OSError):
        TextFileWriter().write([ExamSchedule()], str(tmp_path))

    captured = capsys.readouterr()
    assert captured.err == ""
