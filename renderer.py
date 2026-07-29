"""Visual feedback: plain output and coloured terminal rendering.

Two renderers share one interface so the entry point never branches on
"are colours enabled":

* :class:`PlainRenderer` prints strictly the mandated output format;
* :class:`TerminalRenderer` adds an ANSI coloured, turn-by-turn board
  that shows where every drone is and how full each zone is.
"""

from abc import ABC, abstractmethod

from network import Network
from simulator import SimulationResult
from zone import Zone

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
PALETTE: dict[str, str] = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "purple": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "gray": "\033[90m",
    "grey": "\033[90m",
    "orange": "\033[38;5;208m",
    "pink": "\033[38;5;205m",
}
TYPE_FALLBACK: dict[str, str] = {
    "normal": "\033[37m",
    "blocked": "\033[90m",
    "restricted": "\033[31m",
    "priority": "\033[36m",
}


class Renderer(ABC):
    """Common interface of every renderer."""

    @abstractmethod
    def show_network(self, network: Network) -> None:
        """Print a summary of the parsed network."""

    @abstractmethod
    def show_simulation(self, result: SimulationResult) -> None:
        """Print the turn-by-turn simulation."""

    @abstractmethod
    def show_metrics(self, result: SimulationResult) -> None:
        """Print the scoring metrics of a finished simulation."""


class PlainRenderer(Renderer):
    """Emit exactly the output format required by the subject."""

    def show_network(self, network: Network) -> None:
        """Print nothing: the plain format carries movements only."""

    def show_simulation(self, result: SimulationResult) -> None:
        """Print one line per turn listing that turn's movements."""
        for record in result.records:
            print(record.render())

    def show_metrics(self, result: SimulationResult) -> None:
        """Print nothing: metrics are optional extra output."""


class TerminalRenderer(Renderer):
    """Coloured, human friendly view of the same simulation."""

    def __init__(self, use_color: bool = True) -> None:
        """Create a renderer, optionally with colours disabled."""
        self._use_color = use_color

    def _paint(self, text: str, code: str) -> str:
        """Wrap ``text`` in an ANSI escape when colours are enabled."""
        if not self._use_color or not code:
            return text
        return f"{code}{text}{RESET}"

    def _zone_color(self, zone: Zone) -> str:
        """Return the ANSI code chosen for a zone."""
        declared = zone.color
        if declared is not None:
            return PALETTE.get(declared.lower(), "")
        return TYPE_FALLBACK.get(zone.zone_type.value, "")

    def show_network(self, network: Network) -> None:
        """Print the zones, their type, capacity and their links."""
        print(self._paint("Network", BOLD))
        print(f"  drones     : {network.nb_drones}")
        print(f"  zones      : {len(network.zones)}")
        print(f"  connections: {len(network.connections)}")
        print(f"  start      : {network.start.name}")
        print(f"  end        : {network.end.name}")
        print()
        print(self._paint("Zones", BOLD))
        for zone in network.zones:
            capacity = zone.capacity
            room = "inf" if capacity is None else str(capacity)
            label = self._paint(f"{zone.name:<18}", self._zone_color(zone))
            print(
                f"  {label} type={zone.zone_type.value:<10} "
                f"cost={zone.move_cost} capacity={room:<4} "
                f"({zone.x},{zone.y})"
            )
        print()
        print(self._paint("Connections", BOLD))
        for connection in network.connections:
            print(
                f"  {connection.name:<28} "
                f"max_link_capacity={connection.capacity}"
            )
        print()

    def show_routes(self, result: SimulationResult) -> None:
        """Print the routes chosen by the planner and their load."""
        plan = result.plan
        print(self._paint("Chosen routes", BOLD))
        for index, route in enumerate(plan.routes):
            arrow = " -> ".join(route)
            print(
                f"  [{plan.loads[index]:>3} drones | cost "
                f"{plan.costs[index]:>3}] {arrow}"
            )
        print()

    def show_simulation(self, result: SimulationResult) -> None:
        """Print each turn with its movements and the fleet progress."""
        total = len(result.drones)
        print(self._paint("Simulation", BOLD))
        delivered = 0
        for record in result.records:
            delivered = sum(
                1
                for drone in result.drones
                if drone.delivery_turn and drone.delivery_turn <= record.number
            )
            header = self._paint(f"turn {record.number:>3}", BOLD)
            gauge = self._gauge(delivered, total)
            print(f"  {header} {gauge} {record.render()}")
        print()

    def _gauge(self, delivered: int, total: int) -> str:
        """Return a small textual progress bar."""
        width = 20
        if total <= 0:
            filled = width
        else:
            filled = int(width * delivered / total)
        bar = "#" * filled + "." * (width - filled)
        return self._paint(f"[{bar}] {delivered:>3}/{total}", DIM)

    def show_metrics(self, result: SimulationResult) -> None:
        """Print the primary score and the secondary metrics."""
        print(self._paint("Metrics", BOLD))
        print(f"  total turns          : {result.turns}")
        print(f"  routes used          : {result.plan.width}")
        print(f"  movements            : {result.total_moves}")
        print(f"  movements per turn   : {result.moves_per_turn:.2f}")
        print(
            "  average turns/drone  : "
            f"{result.average_turns_per_drone:.2f}"
        )
        print(f"  total path cost      : {result.total_path_cost}")
        print()
