"""Tests for :mod:`drone`: the per-drone movement state machine."""

import pytest

from drone import Drone, DroneState
from errors import SimulationError


def test_a_route_needs_at_least_a_start_and_a_destination() -> None:
    with pytest.raises(SimulationError):
        Drone(1, ("start",))


def test_new_drone_starts_at_zone_zero() -> None:
    drone = Drone(1, ("start", "goal"))
    assert drone.state is DroneState.AT_ZONE
    assert drone.zone_name == "start"
    assert drone.origin_name == "start"
    assert drone.target_name == "goal"
    assert drone.label == "D1"
    assert drone.has_arrived() is False


def test_step_moves_to_the_next_zone() -> None:
    drone = Drone(2, ("start", "mid", "goal"))
    drone.step()
    assert drone.position == 1
    assert drone.zone_name == "mid"
    assert drone.has_arrived() is False


def test_step_is_rejected_while_in_flight() -> None:
    drone = Drone(1, ("start", "gate", "goal"))
    drone.begin_flight(1)
    with pytest.raises(SimulationError):
        drone.step()


def test_target_name_past_the_last_zone_raises() -> None:
    drone = Drone(1, ("start", "goal"))
    drone.step()
    with pytest.raises(SimulationError):
        drone.target_name


def test_begin_flight_requires_at_least_one_turn() -> None:
    drone = Drone(1, ("start", "gate"))
    with pytest.raises(SimulationError):
        drone.begin_flight(0)


def test_begin_flight_switches_state_and_hides_the_zone() -> None:
    drone = Drone(1, ("start", "gate"))
    drone.begin_flight(1)
    assert drone.is_in_flight is True
    with pytest.raises(SimulationError):
        drone.zone_name


def test_begin_flight_twice_is_rejected() -> None:
    drone = Drone(1, ("start", "gate"))
    drone.begin_flight(1)
    with pytest.raises(SimulationError):
        drone.begin_flight(1)


def test_continue_flight_lands_after_the_requested_turns() -> None:
    drone = Drone(1, ("start", "gate"))
    drone.begin_flight(2)
    assert drone.continue_flight() is False
    assert drone.is_in_flight is True
    assert drone.continue_flight() is True
    assert drone.is_in_flight is False
    assert drone.zone_name == "gate"


def test_continue_flight_while_grounded_raises() -> None:
    drone = Drone(1, ("start", "goal"))
    with pytest.raises(SimulationError):
        drone.continue_flight()


def test_mark_delivered_records_the_turn() -> None:
    drone = Drone(1, ("start", "goal"))
    drone.step()
    drone.mark_delivered(7)
    assert drone.is_delivered is True
    assert drone.delivery_turn == 7


def test_has_arrived_true_on_the_last_route_zone() -> None:
    drone = Drone(1, ("start", "goal"))
    drone.step()
    assert drone.has_arrived() is True
