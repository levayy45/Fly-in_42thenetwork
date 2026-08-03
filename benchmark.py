"""Run every shipped map and compare the result to its turn target.

Usage:
    python3 benchmark.py
"""

import glob
import os
import sys

from errors import FlyInError
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
    "01_the_impossible_dream.txt": 45,
}

# The challenger map is explicitly optional and never affects the grade,
# so missing its target must not fail the benchmark run.
OPTIONAL_MAPS: frozenset[str] = frozenset({"01_the_impossible_dream.txt"})


class Benchmark:
    """Solve a set of maps and report turns against the targets."""

    def __init__(self, pattern: str) -> None:
        """Store the glob pattern of the maps to benchmark."""
        self._pattern = pattern

    def run(self) -> int:
        """Print one report line per map and return the exit code."""
        paths = sorted(glob.glob(self._pattern))
        if not paths:
            print(f"no map matched {self._pattern!r}", file=sys.stderr)
            return 1
        failures = 0
        header = f"{'map':<36}{'drones':>7}{'turns':>7}{'target':>8}  status"
        print(header)
        print("-" * len(header))
        for path in paths:
            failures += self._report(path)
        print()
        if failures:
            print(f"{failures} map(s) missed their target")
        else:
            print("every map met its target")
        return 1 if failures else 0

    def _report(self, path: str) -> int:
        """Solve one map and print its line, returning 1 on failure."""
        name = os.path.basename(path)
        target = TARGETS.get(name, 0)
        try:
            network = MapParser().parse_file(path)
            plans = Router(network).candidate_plans()
            result = PlanSelector(network).best(plans)
            SimulationVerifier(network).verify(
                result.render().splitlines()
            )
        except (FlyInError, OSError) as error:
            print(f"{name:<36}{'-':>7}{'-':>7}{target:>8}  FAILED {error}")
            return 1
        ok = target <= 0 or result.turns <= target
        optional = name in OPTIONAL_MAPS
        if ok:
            status = "ok"
        elif optional:
            status = "over target (optional, no grade impact)"
        else:
            status = "OVER TARGET"
        print(
            f"{name:<36}{network.nb_drones:>7}{result.turns:>7}"
            f"{target:>8}  {status}"
        )
        return 0 if ok or optional else 1


def main() -> int:
    """Benchmark every map shipped under ``maps/``."""
    pattern = os.path.join("maps", "*", "*.txt")
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    return Benchmark(pattern).run()


if __name__ == "__main__":
    sys.exit(main())
