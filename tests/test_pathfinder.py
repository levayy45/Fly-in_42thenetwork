"""Tests for :mod:`pathfinder`: single drone Dijkstra with priority bias."""

import pytest

from connection import Connection
from errors import NoRouteError
from network import Network
from pathfinder import ShortestPathFinder
from zone import Zone, ZoneRole, ZoneType


def test_straight_line_cost_is_the_sum_of_entry_costs() -> None:
    network = Network(1)
    network.add_zone(Zone("start", 0, 0, ZoneRole.START))
    network.add_zone(Zone("mid", 1, 0, ZoneRole.REGULAR))
    network.add_zone(Zone("goal", 2, 0, ZoneRole.END))
    network.add_connection(Connection("start", "mid"))
    network.add_connection(Connection("mid", "goal"))
    path = ShortestPathFinder(network).best_path()
    assert path == ("start", "mid", "goal")


def _fork_network(mid_type: ZoneType) -> Network:
    """Two equal-length forks: one plain, one of the requested type."""
    network = Network(1)
    network.add_zone(Zone("start", 0, 0, ZoneRole.START))
    network.add_zone(Zone("goal", 2, 0, ZoneRole.END))
    network.add_zone(Zone("plain", 1, 1, ZoneRole.REGULAR))
    network.add_zone(
        Zone("special", 1, -1, ZoneRole.REGULAR, zone_type=mid_type)
    )
    network.add_connection(Connection("start", "plain"))
    network.add_connection(Connection("plain", "goal"))
    network.add_connection(Connection("start", "special"))
    network.add_connection(Connection("special", "goal"))
    return network


def test_priority_zone_is_preferred_without_changing_the_turn_count() -> None:
    network = _fork_network(ZoneType.PRIORITY)
    path = ShortestPathFinder(network).best_path()
    assert "special" in path
    assert network.path_cost(path) == 2  # still a plain 2-turn path


def test_between_two_equally_plain_forks_either_is_acceptable() -> None:
    network = _fork_network(ZoneType.NORMAL)
    path = ShortestPathFinder(network).best_path()
    assert network.path_cost(path) == 2


def test_restricted_zone_costs_two_turns() -> None:
    network = Network(1)
    network.add_zone(Zone("start", 0, 0, ZoneRole.START))
    network.add_zone(
        Zone(
            "gate", 1, 0, ZoneRole.REGULAR, zone_type=ZoneType.RESTRICTED
        )
    )
    network.add_zone(Zone("goal", 2, 0, ZoneRole.END))
    network.add_connection(Connection("start", "gate"))
    network.add_connection(Connection("gate", "goal"))
    path = ShortestPathFinder(network).best_path()
    assert network.path_cost(path) == 3


def test_blocked_start_hub_has_no_route() -> None:
    network = Network(1)
    network.add_zone(
        Zone(
            "start", 0, 0, ZoneRole.START, zone_type=ZoneType.BLOCKED
        )
    )
    network.add_zone(Zone("goal", 1, 0, ZoneRole.END))
    with pytest.raises(NoRouteError):
        ShortestPathFinder(network).best_path()


def test_disconnected_end_hub_has_no_route() -> None:
    network = Network(1)
    network.add_zone(Zone("start", 0, 0, ZoneRole.START))
    network.add_zone(Zone("goal", 1, 0, ZoneRole.END))
    with pytest.raises(NoRouteError):
        ShortestPathFinder(network).best_path()


def test_blocked_zone_is_never_walked_through() -> None:
    network = Network(1)
    network.add_zone(Zone("start", 0, 0, ZoneRole.START))
    network.add_zone(
        Zone("wall", 1, 0, ZoneRole.REGULAR, zone_type=ZoneType.BLOCKED)
    )
    network.add_zone(Zone("goal", 2, 0, ZoneRole.END))
    network.add_connection(Connection("start", "wall"))
    network.add_connection(Connection("wall", "goal"))
    with pytest.raises(NoRouteError):
        ShortestPathFinder(network).best_path()
