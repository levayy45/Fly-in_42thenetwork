"""Tests for :mod:`renderer`: plain and terminal output."""

import pytest

from network import Network
from parser import MapParser
from renderer import PlainRenderer, TerminalRenderer
from router import Router
from simulator import PlanSelector, SimulationResult


def solved() -> tuple[Network, SimulationResult]:
    network = MapParser().parse_lines(
        [
            "nb_drones: 2",
            "start_hub: start 0 0 [color=green]",
            "end_hub: goal 2 0 [color=red]",
            "hub: mid 1 0 [max_drones=2]",
            "connection: start-mid [max_link_capacity=2]",
            "connection: mid-goal [max_link_capacity=2]",
        ]
    )
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    return network, result


def test_plain_renderer_prints_only_the_mandated_movement_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, result = solved()
    renderer = PlainRenderer()
    renderer.show_network(Network(1))
    renderer.show_simulation(result)
    renderer.show_metrics(result)
    out = capsys.readouterr().out
    assert out.strip().splitlines() == result.render().splitlines()


def test_terminal_renderer_network_view_lists_every_zone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, _ = solved()
    TerminalRenderer(use_color=False).show_network(network)
    out = capsys.readouterr().out
    for zone in network.zones:
        assert zone.name in out


def test_terminal_renderer_no_color_has_no_ansi_escapes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, result = solved()
    renderer = TerminalRenderer(use_color=False)
    renderer.show_network(network)
    renderer.show_routes(result)
    renderer.show_simulation(result)
    renderer.show_metrics(result)
    out = capsys.readouterr().out
    assert "\033[" not in out


def test_terminal_renderer_with_color_does_use_ansi_escapes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    network, _ = solved()
    TerminalRenderer(use_color=True).show_network(network)
    out = capsys.readouterr().out
    assert "\033[" in out


def test_terminal_renderer_metrics_reports_the_turn_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, result = solved()
    TerminalRenderer(use_color=False).show_metrics(result)
    out = capsys.readouterr().out
    assert f"total turns          : {result.turns}" in out
