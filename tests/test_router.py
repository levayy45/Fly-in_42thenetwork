"""Tests for :mod:`router`: flow-based route planning."""

from network import Network
from parser import MapParser
from router import Router


def build(*lines: str) -> Network:
    return MapParser().parse_lines(list(lines))


def test_single_path_produces_one_route_carrying_the_whole_fleet() -> None:
    network = build(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0",
        "connection: start-mid",
        "connection: mid-goal",
    )
    plans = Router(network).candidate_plans()
    assert len(plans) == 1
    assert plans[0].width == 1
    assert plans[0].loads == (3,)
    assert plans[0].estimate == 2 + 3 - 1


def test_two_disjoint_paths_yield_a_wider_faster_candidate() -> None:
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
    widths = {plan.width: plan for plan in plans}
    assert 1 in widths and 2 in widths
    # Each route costs 2 turns (entering the fork zone, then the goal).
    assert widths[1].estimate == 2 + 4 - 1
    assert widths[2].estimate == 2 + 2 - 1
    # Cheapest estimate first.
    assert plans[0].estimate <= plans[-1].estimate


def test_shared_bottleneck_zone_caps_the_number_of_usable_routes() -> None:
    # Two topologically distinct paths (via 'a' and via 'b') both funnel
    # through a shared zone whose capacity allows only one unit of flow,
    # so only one of them can ever be part of a candidate plan.
    network = build(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 3 0",
        "hub: a 1 1",
        "hub: b 1 -1",
        "hub: gate 2 0 [max_drones=1]",
        "connection: start-a",
        "connection: start-b",
        "connection: a-gate",
        "connection: b-gate",
        "connection: gate-goal",
    )
    plans = Router(network).candidate_plans()
    assert len(plans) == 1
    assert plans[0].width == 1


def test_drone_routes_interleaves_cheapest_route_first() -> None:
    network = build(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0",
        "connection: start-mid",
        "connection: mid-goal",
    )
    plan = Router(network).candidate_plans()[0]
    routes = plan.drone_routes()
    assert len(routes) == 3
    assert all(route == ("start", "mid", "goal") for route in routes)
