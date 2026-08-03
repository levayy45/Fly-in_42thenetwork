"""Tests for :mod:`connection`."""

import pytest

from connection import Connection
from errors import NetworkError


def test_name_keeps_the_declared_orientation() -> None:
    connection = Connection("a", "b")
    assert connection.name == "a-b"
    assert Connection("b", "a").name == "b-a"


def test_key_is_orientation_independent() -> None:
    assert Connection("a", "b").key == Connection("b", "a").key


def test_endpoints_and_other() -> None:
    connection = Connection("a", "b", capacity=3)
    assert connection.endpoints() == ("a", "b")
    assert connection.capacity == 3
    assert connection.other("a") == "b"
    assert connection.other("b") == "a"


def test_other_rejects_a_foreign_zone() -> None:
    connection = Connection("a", "b")
    with pytest.raises(NetworkError):
        connection.other("c")
