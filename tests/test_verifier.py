"""Tests for :mod:`verifier`: independent replay of a simulation output."""

import pytest

from errors import SimulationError
from network import Network
from parser import MapParser
from router import Router
from simulator import PlanSelector
from verifier import SimulationVerifier


def build(*lines: str) -> Network:
    return MapParser().parse_lines(list(lines))


def solve(network: Network) -> list[str]:
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    return result.render().splitlines()


def test_verifier_accepts_a_genuine_simulator_run() -> None:
    network = build(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=2]",
        "connection: start-mid",
        "connection: mid-goal",
    )
    lines = solve(network)
    turns = SimulationVerifier(network).verify(lines)
    assert turns == len(lines)


def test_verifier_accepts_a_restricted_zone_crossing() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: gate 1 0 [zone=restricted]",
        "connection: start-gate",
        "connection: gate-goal",
    )
    lines = solve(network)
    assert SimulationVerifier(network).verify(lines) == len(lines)


def _network() -> Network:
    return build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0",
        "connection: start-mid",
        "connection: mid-goal",
    )


def test_rejects_a_drone_moving_twice_in_one_turn() -> None:
    with pytest.raises(SimulationError):
        SimulationVerifier(_network()).verify(["D1-mid D1-mid"])


def test_rejects_a_malformed_token() -> None:
    with pytest.raises(SimulationError):
        SimulationVerifier(_network()).verify(["D1"])


def test_rejects_an_unknown_drone_id() -> None:
    with pytest.raises(SimulationError):
        SimulationVerifier(_network()).verify(["D9-mid"])


def test_rejects_a_jump_without_a_connection() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0",
        "hub: island 1 5",
        "connection: start-mid",
        "connection: mid-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(["D1-island"])


def test_rejects_exceeding_zone_capacity() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=1]",
        "connection: start-mid [max_link_capacity=2]",
        "connection: mid-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(["D1-mid D2-mid"])


def test_rejects_exceeding_link_capacity() -> None:
    network = build(
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [max_drones=2]",
        "connection: start-mid",
        "connection: mid-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(["D1-mid D2-mid"])


def test_rejects_a_move_after_delivery() -> None:
    network = _network()
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(
            ["D1-mid D2-mid", "D1-goal D2-goal", "D1-mid"]
        )


def test_rejects_landing_from_flight_on_the_wrong_zone() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: gate 1 0 [zone=restricted]",
        "hub: other 1 5",
        "connection: start-gate",
        "connection: gate-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(
            ["D1-start-gate", "D1-other"]
        )


def test_rejects_entering_a_blocked_zone() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: wall 1 0 [zone=blocked]",
        "connection: start-wall",
        "connection: wall-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(["D1-wall"])


def test_ending_the_run_with_a_drone_still_in_flight_is_rejected() -> None:
    network = build(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: gate 1 0 [zone=restricted]",
        "connection: start-gate",
        "connection: gate-goal",
    )
    with pytest.raises(SimulationError):
        SimulationVerifier(network).verify(["D1-start-gate"])
