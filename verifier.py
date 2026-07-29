"""Independent replay of a simulation output against the rules.

The simulator and the verifier share no code path on purpose. The
simulator decides the movements; the verifier reads the printed lines
back, replays them on the network and refuses anything that breaks a
rule. Capacity is checked on the *end of turn* state, which is exactly
what the subject describes when it says a drone leaving a zone frees its
slot during the same turn.

This is what makes the output trustworthy: if the verifier accepts a run,
the run is legal.
"""

from collections import Counter

from connection import Connection
from errors import SimulationError
from network import Network


class Flight:
    """A drone currently crossing a connection."""

    def __init__(
        self,
        connection: Connection,
        target: str,
        remaining: int,
    ) -> None:
        """Store the link, the destination zone and the turns left."""
        self.connection = connection
        self.target = target
        self.remaining = remaining


class SimulationVerifier:
    """Replay printed movement lines and assert every rule holds."""

    def __init__(self, network: Network) -> None:
        """Bind the verifier to a network and index the link names."""
        self._network = network
        self._links = {
            connection.name: connection
            for connection in network.connections
        }

    def verify(self, lines: list[str]) -> int:
        """Replay ``lines`` and return the number of turns.

        Args:
            lines: The simulation output, one string per turn.

        Returns:
            The number of turns replayed.

        Raises:
            SimulationError: On the first rule violation found.
        """
        fleet = self._network.nb_drones
        start = self._network.start.name
        positions = {number: start for number in range(1, fleet + 1)}
        flights: dict[int, Flight] = {}
        delivered: set[int] = set()
        for index, line in enumerate(lines, start=1):
            self._replay_turn(
                index, line, positions, flights, delivered
            )
        if flights:
            raise SimulationError(
                "the run ends with drones still crossing a connection"
            )
        missing = sorted(set(positions) - delivered)
        if missing:
            labels = ", ".join(f"D{number}" for number in missing)
            raise SimulationError(f"never delivered: {labels}")
        return len(lines)

    def _replay_turn(
        self,
        turn: int,
        line: str,
        positions: dict[int, str],
        flights: dict[int, Flight],
        delivered: set[int],
    ) -> None:
        """Replay a single turn and check the resulting state."""
        moves = self._parse(turn, line, positions, delivered)
        links: Counter[frozenset[str]] = Counter()
        for number, flight in flights.items():
            links[flight.connection.key] += 1
            if number not in moves:
                raise SimulationError(
                    f"turn {turn}: D{number} is in flight but was not "
                    "reported, a drone may not wait on a connection"
                )
        for number, token in sorted(moves.items()):
            if number in flights:
                self._land(turn, number, token, positions, flights)
            else:
                self._depart(
                    turn, number, token, positions, flights, links
                )
        self._check_links(turn, links)
        self._check_zones(turn, positions, flights, delivered)
        for number, zone_name in list(positions.items()):
            if zone_name == self._network.end.name:
                delivered.add(number)

    def _parse(
        self,
        turn: int,
        line: str,
        positions: dict[int, str],
        delivered: set[int],
    ) -> dict[int, str]:
        """Split one output line into a ``drone -> destination`` map."""
        moves: dict[int, str] = {}
        for token in line.split():
            if not token.startswith("D") or "-" not in token:
                raise SimulationError(
                    f"turn {turn}: malformed movement {token!r}"
                )
            head, destination = token[1:].split("-", 1)
            try:
                number = int(head)
            except ValueError:
                raise SimulationError(
                    f"turn {turn}: malformed drone id in {token!r}"
                ) from None
            if number not in positions:
                raise SimulationError(
                    f"turn {turn}: unknown drone D{number}"
                )
            if number in delivered:
                raise SimulationError(
                    f"turn {turn}: D{number} moves after being delivered"
                )
            if number in moves:
                raise SimulationError(
                    f"turn {turn}: D{number} moves twice in one turn"
                )
            moves[number] = destination
        return moves

    def _land(
        self,
        turn: int,
        number: int,
        token: str,
        positions: dict[int, str],
        flights: dict[int, Flight],
    ) -> None:
        """Apply the landing of an in-flight drone."""
        flight = flights[number]
        if token != flight.target:
            raise SimulationError(
                f"turn {turn}: D{number} must land on "
                f"{flight.target!r} but reports {token!r}"
            )
        flight.remaining -= 1
        if flight.remaining > 0:
            raise SimulationError(
                f"turn {turn}: D{number} landed too early on {token!r}"
            )
        positions[number] = flight.target
        del flights[number]

    def _depart(
        self,
        turn: int,
        number: int,
        token: str,
        positions: dict[int, str],
        flights: dict[int, Flight],
        links: Counter[frozenset[str]],
    ) -> None:
        """Apply a one-turn move or the departure of a longer crossing."""
        origin = positions[number]
        if self._network.has_zone(token):
            link = self._require_link(turn, number, origin, token)
            zone = self._network.zone(token)
            if not zone.is_passable:
                raise SimulationError(
                    f"turn {turn}: D{number} enters the blocked zone "
                    f"{token!r}"
                )
            if zone.move_cost != 1:
                raise SimulationError(
                    f"turn {turn}: D{number} reaches {token!r} in one "
                    f"turn but it costs {zone.move_cost}"
                )
            links[link.key] += 1
            positions[number] = token
            return
        connection = self._links.get(token)
        if connection is None:
            raise SimulationError(
                f"turn {turn}: {token!r} is neither a zone nor a "
                "connection"
            )
        if origin not in connection.endpoints():
            raise SimulationError(
                f"turn {turn}: D{number} is in {origin!r} and cannot "
                f"enter the connection {token!r}"
            )
        target = connection.other(origin)
        zone = self._network.zone(target)
        if not zone.is_passable:
            raise SimulationError(
                f"turn {turn}: D{number} heads for the blocked zone "
                f"{target!r}"
            )
        if zone.move_cost < 2:
            raise SimulationError(
                f"turn {turn}: D{number} occupies {token!r} although "
                f"{target!r} is reachable in one turn"
            )
        links[connection.key] += 1
        flights[number] = Flight(connection, target, zone.move_cost - 1)

    def _require_link(
        self,
        turn: int,
        number: int,
        origin: str,
        target: str,
    ) -> Connection:
        """Return the connection between two zones or fail loudly."""
        if not self._network.has_connection(origin, target):
            raise SimulationError(
                f"turn {turn}: D{number} jumps from {origin!r} to "
                f"{target!r} without a connection"
            )
        return self._network.connection(origin, target)

    def _check_links(
        self,
        turn: int,
        links: Counter[frozenset[str]],
    ) -> None:
        """Assert no connection carried more drones than allowed."""
        for key, used in links.items():
            first, second = tuple(key) if len(key) == 2 else (
                next(iter(key)),
                next(iter(key)),
            )
            connection = self._network.connection(first, second)
            if used > connection.capacity:
                raise SimulationError(
                    f"turn {turn}: {used} drones crossed "
                    f"{connection.name!r} but its capacity is "
                    f"{connection.capacity}"
                )

    def _check_zones(
        self,
        turn: int,
        positions: dict[int, str],
        flights: dict[int, Flight],
        delivered: set[int],
    ) -> None:
        """Assert no zone held more drones than allowed."""
        occupancy: Counter[str] = Counter()
        for number, zone_name in positions.items():
            if number in delivered or number in flights:
                continue
            occupancy[zone_name] += 1
        for zone_name, count in occupancy.items():
            zone = self._network.zone(zone_name)
            if not zone.accepts(count - 1):
                raise SimulationError(
                    f"turn {turn}: {count} drones sit in "
                    f"{zone_name!r} whose capacity is {zone.capacity}"
                )
