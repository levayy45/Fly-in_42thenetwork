"""Entry point of the Fly-in drone routing simulator.

Usage:
    python3 main.py maps/easy/01_linear_path.txt
    python3 main.py maps/hard/02_capacity_hell.txt --visual --metrics
"""

import argparse
import sys

from errors import FlyInError
from network import Network
from parser import MapParser
from renderer import PlainRenderer, Renderer, TerminalRenderer
from router import Router
from simulator import PlanSelector, SimulationResult
from verifier import SimulationVerifier


class Application:
    """Wire the parser, the router, the simulator and the renderers."""

    def __init__(self) -> None:
        """Create an application with a fresh parser."""
        self._parser = MapParser()

    def build_arguments(self) -> argparse.ArgumentParser:
        """Return the command line interface description."""
        parser = argparse.ArgumentParser(
            prog="flyin",
            description=(
                "Route a fleet of drones from the start hub to the end "
                "hub in as few simulation turns as possible."
            ),
        )
        parser.add_argument("map_file", help="path to the map file")
        parser.add_argument(
            "-v",
            "--visual",
            action="store_true",
            help="show the coloured network, routes and progress view",
        )
        parser.add_argument(
            "-m",
            "--metrics",
            action="store_true",
            help="show the scoring metrics after the simulation",
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="disable ANSI colours in the visual view",
        )
        parser.add_argument(
            "--verify",
            action="store_true",
            help="replay the output and assert every rule is respected",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="hide the plain per-turn movement lines",
        )
        return parser

    def run(self, argv: list[str]) -> int:
        """Execute one full run and return the process exit code.

        Args:
            argv: Command line arguments without the program name.

        Returns:
            ``0`` on success, ``1`` on any handled failure.
        """
        options = self.build_arguments().parse_args(argv)
        try:
            network = self._parser.parse_file(options.map_file)
            result = self._solve(network)
            if options.verify:
                self._verify(network, result)
        except FlyInError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        except OSError as error:
            print(f"error: cannot read the map file: {error}",
                  file=sys.stderr)
            return 1
        self._report(options, network, result)
        return 0

    def _solve(self, network: Network) -> SimulationResult:
        """Plan the routes and simulate the fastest valid plan."""
        router = Router(network)
        plans = router.candidate_plans()
        selector = PlanSelector(network)
        return selector.best(plans)

    def _verify(
        self,
        network: Network,
        result: SimulationResult,
    ) -> None:
        """Replay the output through the independent rule checker."""
        verifier = SimulationVerifier(network)
        turns = verifier.verify(result.render().splitlines())
        print(f"verified: {turns} legal turns", file=sys.stderr)

    def _report(
        self,
        options: argparse.Namespace,
        network: Network,
        result: SimulationResult,
    ) -> None:
        """Print the requested views of a finished simulation."""
        if options.visual:
            visual = TerminalRenderer(use_color=not options.no_color)
            visual.show_network(network)
            visual.show_routes(result)
            visual.show_simulation(result)
        if not options.quiet:
            plain: Renderer = PlainRenderer()
            plain.show_simulation(result)
        if options.metrics:
            metrics = TerminalRenderer(use_color=not options.no_color)
            metrics.show_metrics(result)


def main() -> int:
    """Run the application with the process arguments."""
    return Application().run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
