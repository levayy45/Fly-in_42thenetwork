"""Tests for :mod:`flow`: the hand written min-cost max-flow solver."""

from flow import MinCostFlow


def test_augment_prefers_the_cheaper_path() -> None:
    # 0 -source, 1 -cheap mid, 2 -sink, 3 -expensive mid.
    graph = MinCostFlow(4)
    graph.add_edge(0, 1, 1, 1)
    graph.add_edge(1, 2, 1, 1)
    graph.add_edge(0, 3, 5, 5)
    graph.add_edge(3, 2, 5, 1)

    first = graph.augment(0, 2, 1)
    assert first == 1
    snapshot = graph.flow_snapshot()
    assert snapshot[0][0] == 1  # 0 -> 1 (cheap path) carried the unit
    assert snapshot[0][1] == 0  # 0 -> 3 (expensive path) untouched


def test_augment_falls_back_to_the_next_cheapest_path_once_saturated() -> None:
    graph = MinCostFlow(4)
    graph.add_edge(0, 1, 1, 1)
    graph.add_edge(1, 2, 1, 1)
    graph.add_edge(0, 3, 5, 5)
    graph.add_edge(3, 2, 5, 1)

    graph.augment(0, 2, 1)
    second = graph.augment(0, 2, 1)
    assert second == 1
    snapshot = graph.flow_snapshot()
    assert snapshot[0][1] == 1  # the second unit had to use the alt path


def test_augment_respects_the_bottleneck_capacity() -> None:
    graph = MinCostFlow(3)
    graph.add_edge(0, 1, 2, 1)
    graph.add_edge(1, 2, 1, 1)  # bottleneck: only 1 unit can cross
    pushed = graph.augment(0, 2, 5)
    assert pushed == 1


def test_augment_returns_zero_when_the_sink_is_unreachable() -> None:
    graph = MinCostFlow(3)
    graph.add_edge(0, 1, 1, 1)  # node 2 is isolated
    assert graph.augment(0, 2, 1) == 0


def test_augment_returns_zero_for_a_non_positive_request() -> None:
    graph = MinCostFlow(2)
    graph.add_edge(0, 1, 1, 1)
    assert graph.augment(0, 1, 0) == 0


def test_add_edge_creates_a_zero_capacity_reverse_arc() -> None:
    graph = MinCostFlow(2)
    graph.add_edge(0, 1, 3, 2)
    forward = graph.outgoing(0)[0]
    backward = graph.outgoing(1)[0]
    assert forward.capacity == 3
    assert forward.cost == 2
    assert backward.capacity == 0
    assert backward.cost == -2


def test_flow_property_tracks_usage_after_augmenting() -> None:
    graph = MinCostFlow(2)
    graph.add_edge(0, 1, 3, 1)
    graph.augment(0, 1, 2)
    assert graph.outgoing(0)[0].flow == 2
    assert graph.outgoing(0)[0].capacity == 1
