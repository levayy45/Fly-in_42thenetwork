"""End-to-end regression tests: solve every shipped map and check it.

These close the loop between the pytest suite and ``benchmark.py``: the
full parse -> route -> simulate -> verify pipeline must both succeed and
meet the subject's turn targets on every map actually shipped in
``maps/``.
"""

from pathlib import Path

import pytest

from conftest import MAPS_DIR
from parser import MapParser
from router import Router
from simulator import PlanSelector
from verifier import SimulationVerifier

TARGETS: dict[str, int] = {
    "01_linear_path.txt": 6,
    "02_simple_fork.txt": 8,
    "03_basic_capacity.txt": 6,
    "01_dead_end_trap.txt": 12,
    "02_circular_loop.txt": 15,
    "03_priority_puzzle.txt": 12,
    "01_maze_nightmare.txt": 30,
    "02_capacity_hell.txt": 35,
    "03_ultimate_challenge.txt": 45,
}

MANDATORY_MAPS: list[Path] = sorted(
    path
    for path in MAPS_DIR.glob("*/*.txt")
    if path.name in TARGETS
)


@pytest.mark.parametrize(
    "path", MANDATORY_MAPS, ids=[path.stem for path in MANDATORY_MAPS]
)
def test_mandatory_map_meets_its_performance_target(path: Path) -> None:
    network = MapParser().parse_file(str(path))
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    SimulationVerifier(network).verify(result.render().splitlines())
    assert result.turns <= TARGETS[path.name]


def test_challenger_map_solves_without_being_held_to_a_grade_target() -> None:
    path = MAPS_DIR / "challenger" / "01_the_impossible_dream.txt"
    network = MapParser().parse_file(str(path))
    plans = Router(network).candidate_plans()
    result = PlanSelector(network).best(plans)
    SimulationVerifier(network).verify(result.render().splitlines())
    assert result.turns > 0
