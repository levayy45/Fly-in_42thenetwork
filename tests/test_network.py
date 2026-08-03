"""Tests for :mod:`network`: the hand written graph container."""

import pytest

from connection import Connection
from errors import NetworkError
from network import Network
from zone import Zone, ZoneRole, ZoneType


def _zone(
    name: str,
    role: ZoneRole = ZoneRole.REGULAR,
    **kwargs: object,
) -> Zone:
    return Zone(name, 0, 0, role, **kwargs)  # type: ignore[arg-type]


def test_start_and_end_raise_before_they_are_registered() -> None:
    network = Network(1)
    with pytest.raises(NetworkError):
        network.start
    with pytest.raises(NetworkError):
        network.end


def test_add_zone_registers_start_and_end() -> None:
    network = Network(1)
    network.add_zone(_zone("start", ZoneRole.START))
    network.add_zone(_zone("goal", ZoneRole.END))
    assert network.start.name == "start"
    assert network.end.name == "goal"
    assert network.has_zone("start") is True
    assert network.has_zone("nowhere") is False


def test_add_zone_rejects_duplicate_names() -> None:
    network = Network(1)
    network.add_zone(_zone("mid"))
    with pytest.raises(NetworkError):
        network.add_zone(_zone("mid"))


def test_add_zone_rejects_a_second_start_or_end_hub() -> None:
    network = Network(1)
    network.add_zone(_zone("start1", ZoneRole.START))
    with pytest.raises(NetworkError):
        network.add_zone(_zone("start2", ZoneRole.START))
    network.add_zone(_zone("goal1", ZoneRole.END))
    with pytest.raises(NetworkError):
        network.add_zone(_zone("goal2", ZoneRole.END))


def test_zone_lookup_of_unknown_name_raises() -> None:
    network = Network(1)
    with pytest.raises(NetworkError):
        network.zone("nowhere")


def test_add_connection_rejects_unknown_endpoint() -> None:
    network = Network(1)
    network.add_zone(_zone("a"))
    with pytest.raises(NetworkError):
        network.add_connection(Connection("a", "b"))


def test_add_connection_rejects_self_loop() -> None:
    network = Network(1)
    network.add_zone(_zone("a"))
    with pytest.raises(NetworkError):
        network.add_connection(Connection("a", "a"))


def test_add_connection_rejects_duplicate_regardless_of_orientation() -> None:
    network = Network(1)
    network.add_zone(_zone("a"))
    network.add_zone(_zone("b"))
    network.add_connection(Connection("a", "b"))
    with pytest.raises(NetworkError):
        network.add_connection(Connection("b", "a"))


def test_neighbours_are_bidirectional() -> None:
    network = Network(1)
    network.add_zone(_zone("a"))
    network.add_zone(_zone("b"))
    network.add_connection(Connection("a", "b"))
    assert network.neighbours("a") == ("b",)
    assert network.neighbours("b") == ("a",)


def test_neighbours_of_unknown_zone_raises() -> None:
    network = Network(1)
    with pytest.raises(NetworkError):
        network.neighbours("nowhere")


def test_connection_lookup_missing_link_raises() -> None:
    network = Network(1)
    network.add_zone(_zone("a"))
    network.add_zone(_zone("b"))
    with pytest.raises(NetworkError):
        network.connection("a", "b")


def test_path_cost_sums_entry_costs_after_the_first_zone() -> None:
    network = Network(1)
    network.add_zone(_zone("start", ZoneRole.START))
    network.add_zone(_zone("mid", zone_type=ZoneType.RESTRICTED))
    network.add_zone(_zone("goal", ZoneRole.END))
    assert network.path_cost(("start", "mid", "goal")) == 2 + 1
    assert network.path_cost(("start",)) == 0
