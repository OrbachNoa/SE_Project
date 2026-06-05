import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helper: run main() with the given argv. SystemExit propagates as expected.
# ---------------------------------------------------------------------------
def _run_main(argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", argv)
    from src.entrypoints.main import main
    main()


# ===========================================================================
# TC-MAIN-001 — Happy path: valid input → exit 0, output file created.
# ===========================================================================
def test_main_valid_input_creates_output_and_exits_cleanly(tmp_path, monkeypatch):
    # Arrange
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(FIXTURES / "courses_valid.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(FIXTURES / "programs_valid.txt"),
        "--output", str(output_path),
    ]
    # Act — main() should return normally, not raise SystemExit.
    _run_main(argv, monkeypatch)
    # Assert
    assert output_path.exists(), "main() did not create the expected output file"
    assert output_path.stat().st_size > 0, "Output file is empty"


# ===========================================================================
# TC-MAIN-002 — Too many programs → clean error, no traceback, exit 1.
# ===========================================================================
def test_main_too_many_programs_clean_error_exit_1(tmp_path, capsys, monkeypatch):
    # Arrange — 6 programs (over the limit of 5)
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(FIXTURES / "courses_valid.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(FIXTURES / "programs_too_many.txt"),
        "--output", str(output_path),
    ]
    # Act
    with pytest.raises(SystemExit) as exc:
        _run_main(argv, monkeypatch)
    # Assert — exit code 1, no traceback, descriptive message, no output file.
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err, (
        "main() leaked a Python traceback on a validation error"
    )
    # The message must reference the specific failure reason.
    assert "5" in captured.err, "Error message must mention the limit (5)"
    assert not output_path.exists(), (
        "Output file should not be created when validation fails"
    )


# ===========================================================================
# TC-MAIN-003 — Invalid program code → clean error, exit 1.
# ===========================================================================
def test_main_invalid_program_code_clean_error_exit_1(tmp_path, capsys, monkeypatch):
    # Arrange — '99999' is not a valid program ID.
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(FIXTURES / "courses_valid.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(FIXTURES / "programs_bad_code.txt"),
        "--output", str(output_path),
    ]
    # Act
    with pytest.raises(SystemExit) as exc:
        _run_main(argv, monkeypatch)
    # Assert
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "99999" in captured.err, "Error must name the invalid program code"
    assert not output_path.exists()


# ===========================================================================
# TC-MAIN-004 — Missing input file → clean error, exit 1.
# ===========================================================================
def test_main_missing_input_file_clean_error_exit_1(tmp_path, capsys, monkeypatch):
    # Arrange — courses path points to a non-existent file
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(tmp_path / "does_not_exist.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(FIXTURES / "programs_valid.txt"),
        "--output", str(output_path),
    ]
    # Act
    with pytest.raises(SystemExit) as exc:
        _run_main(argv, monkeypatch)
    # Assert
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert not output_path.exists()


# ===========================================================================
# TC-MAIN-005 — Empty programs file → clean error (delegates to MaxPrograms).
# ===========================================================================
def test_main_empty_programs_clean_error_exit_1(tmp_path, capsys, monkeypatch):
    # Arrange — empty (well, whitespace-only) programs file.
    empty = tmp_path / "empty_programs.txt"
    empty.write_text(" ", encoding="utf-8")
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(FIXTURES / "courses_valid.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(empty),
        "--output", str(output_path),
    ]
    # Act
    with pytest.raises(SystemExit) as exc:
        _run_main(argv, monkeypatch)
    # Assert
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err


# ===========================================================================
# TC-MAIN-006 — Stack trace MUST NOT appear on any user-facing error.
# ===========================================================================
@pytest.mark.parametrize("programs_fixture", [
    "programs_too_many.txt",
    "programs_bad_code.txt",
])
def test_main_never_shows_traceback_for_user_errors(
    programs_fixture, tmp_path, capsys, monkeypatch,
):
    # Arrange
    output_path = tmp_path / "out.txt"
    argv = [
        "main",
        str(FIXTURES / "courses_valid.txt"),
        str(FIXTURES / "periods_valid.txt"),
        str(FIXTURES / programs_fixture),
        "--output", str(output_path),
    ]
    # Act
    with pytest.raises(SystemExit):
        _run_main(argv, monkeypatch)
    captured = capsys.readouterr()
    # Assert — none of the Python traceback markers.
    assert "Traceback" not in captured.err
    assert 'File "' not in captured.err
    assert "raise " not in captured.err