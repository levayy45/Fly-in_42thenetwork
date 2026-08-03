"""Tests for :mod:`main`: the CLI entry point (``Application``)."""

from pathlib import Path

import pytest

from conftest import MAPS_DIR
from main import Application

EASY_MAP = str(MAPS_DIR / "easy" / "01_linear_path.txt")


def test_run_on_a_valid_map_prints_the_mandated_format_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = Application().run([EASY_MAP])
    out = capsys.readouterr().out
    assert code == 0
    lines = out.strip().splitlines()
    assert lines
    for line in lines:
        assert all(token.startswith("D") for token in line.split())


def test_missing_file_is_a_clean_error_not_a_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = Application().run(["maps/does/not/exist.txt"])
    err = capsys.readouterr().err
    assert code == 1
    assert "error: cannot read the map file" in err


def test_parse_error_reports_the_line_and_returns_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad_map = tmp_path / "broken.map"
    bad_map.write_text("start_hub: start 0 0\nend_hub: goal 1 0\n")
    code = Application().run([str(bad_map)])
    err = capsys.readouterr().err
    assert code == 1
    assert "parse error on line" in err


def test_verify_flag_reports_the_legal_turn_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = Application().run([EASY_MAP, "--verify", "--quiet"])
    err = capsys.readouterr().err
    assert code == 0
    assert "verified:" in err


def test_quiet_suppresses_the_plain_movement_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = Application().run([EASY_MAP, "--quiet", "--metrics"])
    out = capsys.readouterr().out
    assert code == 0
    assert "D1-" not in out
    assert "total turns" in out
