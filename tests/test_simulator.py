"""Tests for :mod:`simulator`: the turn engine and plan selection."""

import pytest

from errors import SimulationError
from network import Network
from parser import MapParser
from router import Router
from simulator import PlanSelector, Simulator


def build(*lines: str) -> Network:
    return MapParser().parse_lines(list(lines))


def run(network: Network) -> str:
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    return result.render()


def test_two_drones_on_a_straight_line_with_room_to_pass_together() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=2]",
        "connection: start-mid [max_link_capacity=2]",
        "connection: mid-goal [max_link_capacity=2]",
    )
    output = run(network).splitlines()
    assert output == ["D1-mid D2-mid", "D1-goal D2-goal"]


def test_default_capacity_of_one_serialises_two_drones() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0",
        "connection: start-mid",
        "connection: mid-goal",
    )
    output = run(network).splitlines()
    assert output == ["D1-mid", "D1-goal D2-mid", "D2-goal"]


def test_zone_capacity_serialises_two_drones_through_a_single_slot() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=1]",
        "connection: start-mid",
        "connection: mid-goal",
    )
    output = run(network).splitlines()
    # Only one drone may occupy 'mid' at a time.
    for line in output:
        assert line.count("-mid") <= 1


def test_link_capacity_limits_simultaneous_crossings() -> None:
    network = build(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=3]",
        "connection: start-mid [max_link_capacity=1]",
        "connection: mid-goal",
    )
    output = run(network).splitlines()
    for line in output:
        assert line.count("-mid") <= 1


def test_restricted_zone_is_reported_as_an_in_flight_connection() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: gate 1 0 [zone=restricted]",
        "connection: start-gate",
        "connection: gate-goal",
    )
    output = run(network).splitlines()
    assert output == ["D1-start-gate", "D1-gate", "D1-goal"]


def test_result_matches_the_mandated_all_delivered_end_state() -> None:
    network = build(
        "nb_drones: 4",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: a 1 1",
        "hub: b 1 -1",
        "connection: start-a",
        "connection: a-goal",
        "connection: start-b",
        "connection: b-goal",
    )
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    assert all(drone.is_delivered for drone in result.drones)
    assert result.turns == len(result.records)
    assert result.total_moves == sum(
        len(record.moves) for record in result.records
    )


def test_simulator_raises_when_the_plan_leaves_a_drone_unrouted() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-goal",
    )
    plans = Router(network).candidate_plans()
    stub_plan = plans[0].__class__(
        routes=plans[0].routes, loads=(1,), costs=plans[0].costs
    )
    with pytest.raises(SimulationError):
        Simulator(network).run(stub_plan)
