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
    "easy_1_linear.map": 6,
    "easy_2_fork.map": 8,
    "easy_3_capacity.map": 6,
    "medium_1_deadend.map": 12,
    "medium_2_loop.map": 15,
    "medium_3_priority.map": 12,
    "hard_1_maze.map": 30,
    "hard_2_capacity.map": 35,
    "hard_3_ultimate.map": 45,
    "challenger_impossible_dream.map": 45,
}


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
        status = "ok" if ok else "OVER TARGET"
        print(
            f"{name:<36}{network.nb_drones:>7}{result.turns:>7}"
            f"{target:>8}  {status}"
        )
        return 0 if ok else 1


def main() -> int:
    """Benchmark every map shipped in ``maps/valid``."""
    pattern = os.path.join("maps", "valid", "*.map")
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    return Benchmark(pattern).run()


if __name__ == "__main__":
    sys.exit(main())
