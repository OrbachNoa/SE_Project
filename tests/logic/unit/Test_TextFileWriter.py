"""Unit tests for TextFileWriter's write-failure path.

The writer used to print its own "Error: Unable to write..." line to stderr
before re-raising, duplicating the report that the calling boundary already
produces via ExceptionMapperRegistry. It should now just let the exception
propagate, with no local printing.

A directory path can't be opened for writing — open() raises a real OSError
(PermissionError on Windows, IsADirectoryError on POSIX), giving genuine OS
failure behavior without monkeypatching builtins.open.

Conventions:
- Each test carries a unique TC-TFW-NNN identifier in the comment block above
  its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- No fixtures are needed beyond pytest's built-in tmp_path/capsys, so none
  are defined locally and no conftest fixture applies.
"""
import pytest

from src.file_io.writers.TextFileWriter import TextFileWriter
from src.models.ExamSchedule import ExamSchedule


# ===========================================================================
# TC-TFW-001: a write failure (target path is a directory, not a file)
# still propagates — the writer does not swallow it.
# ===========================================================================
def test_text_file_writer_write_failure_still_raises(tmp_path):
    # Arrange
    writer = TextFileWriter()
    schedules = [ExamSchedule()]

    # Act
    with pytest.raises(OSError) as exc_info:
        writer.write(schedules, str(tmp_path))

    # Assert — it must be a genuine OS-level failure (carrying an errno, e.g.
    # IsADirectoryError on POSIX / PermissionError on Windows from open()), not
    # an OSError the writer manufactured itself. pytest.raises(OSError) already
    # pins the type, so re-asserting the type would verify nothing.
    assert exc_info.value.errno is not None


# ===========================================================================
# TC-TFW-002: no local stderr print happens on a write failure — the
# boundary that maps every export error is the only one that reports it.
# ===========================================================================
def test_text_file_writer_write_failure_does_not_print_to_stderr(capsys, tmp_path):
    # Arrange
    writer = TextFileWriter()
    schedules = [ExamSchedule()]

    # Act
    with pytest.raises(OSError):
        writer.write(schedules, str(tmp_path))

    # Assert
    captured = capsys.readouterr()
    assert captured.err == ""
