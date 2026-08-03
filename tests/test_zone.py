"""Tests for :mod:`zone`: ``ZoneType`` and ``Zone``."""

import pytest

from zone import Zone, ZoneRole, ZoneType


def test_zone_type_from_text_round_trips() -> None:
    for member in ZoneType:
        assert ZoneType.from_text(member.value) is member


def test_zone_type_from_text_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        ZoneType.from_text("hazardous")


@pytest.mark.parametrize(
    "zone_type,cost",
    [
        (ZoneType.NORMAL, 1),
        (ZoneType.PRIORITY, 1),
        (ZoneType.RESTRICTED, 2),
    ],
)
def test_move_cost_per_type(zone_type: ZoneType, cost: int) -> None:
    assert zone_type.move_cost == cost


def test_blocked_zone_is_not_passable() -> None:
    assert ZoneType.BLOCKED.is_passable is False
    assert ZoneType.NORMAL.is_passable is True


def test_only_priority_is_preferred() -> None:
    assert ZoneType.PRIORITY.is_preferred is True
    assert ZoneType.NORMAL.is_preferred is False
    assert ZoneType.RESTRICTED.is_preferred is False


def test_start_and_end_hubs_ignore_declared_capacity() -> None:
    start = Zone("start", 0, 0, ZoneRole.START, max_drones=5)
    end = Zone("goal", 1, 0, ZoneRole.END, max_drones=5)
    assert start.capacity is None
    assert end.capacity is None
    assert start.accepts(1000) is True
    assert end.accepts(1000) is True


def test_regular_zone_reports_its_declared_capacity() -> None:
    zone = Zone("mid", 0, 1, ZoneRole.REGULAR, max_drones=2)
    assert zone.capacity == 2
    assert zone.accepts(0) is True
    assert zone.accepts(1) is True
    assert zone.accepts(2) is False


def test_blocked_zone_never_accepts_a_drone() -> None:
    zone = Zone(
        "wall", 0, 1, ZoneRole.REGULAR, zone_type=ZoneType.BLOCKED
    )
    assert zone.accepts(0) is False


def test_zone_defaults() -> None:
    zone = Zone("mid", 3, 4, ZoneRole.REGULAR)
    assert zone.zone_type is ZoneType.NORMAL
    assert zone.color is None
    assert zone.declared_capacity == 1
    assert zone.is_terminal is False
    assert zone.move_cost == 1
