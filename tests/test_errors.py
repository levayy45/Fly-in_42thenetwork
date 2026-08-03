"""Tests for the exception hierarchy in :mod:`errors`."""

from errors import (
    FlyInError,
    NetworkError,
    NoRouteError,
    ParseError,
    SimulationError,
)


def test_every_project_error_is_a_flyinerror() -> None:
    for cls in (NetworkError, NoRouteError, ParseError, SimulationError):
        assert issubclass(cls, FlyInError)


def test_parse_error_message_includes_line_and_content() -> None:
    error = ParseError(5, "  hub: bad-name 1 1  ", "forbidden character")
    message = str(error)
    assert "line 5" in message
    assert "forbidden character" in message
    assert "hub: bad-name 1 1" in message
    assert error.line_number == 5
    assert error.reason == "forbidden character"


def test_parse_error_message_without_a_source_line() -> None:
    error = ParseError(1, "", "the map file declares no nb_drones header")
    message = str(error)
    assert message == (
        "parse error on line 1: the map file declares no nb_drones header"
    )
