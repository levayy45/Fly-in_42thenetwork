"""The zone network: a hand written undirected graph.

No third-party graph library is used. The graph is stored as a name to
:class:`Zone` mapping plus an adjacency list of zone names, which keeps
neighbour lookups O(1) amortised and traversals O(V + E).
"""

from connection import Connection
from errors import NetworkError
from zone import Zone


class Network:
    """Container holding every zone, every connection and the fleet size."""

    def __init__(self, nb_drones: int) -> None:
        """Create an empty network for ``nb_drones`` drones."""
        self._nb_drones = nb_drones
        self._zones: dict[str, Zone] = {}
        self._connections: dict[frozenset[str], Connection] = {}
        self._adjacency: dict[str, list[str]] = {}
        self._start: Zone | None = None
        self._end: Zone | None = None

    @property
    def nb_drones(self) -> int:
        """Return the number of drones to route."""
        return self._nb_drones

    @property
    def start(self) -> Zone:
        """Return the start hub.

        Raises:
            NetworkError: If no start hub was registered.
        """
        if self._start is None:
            raise NetworkError("the network has no start hub")
        return self._start

    @property
    def end(self) -> Zone:
        """Return the end hub.

        Raises:
            NetworkError: If no end hub was registered.
        """
        if self._end is None:
            raise NetworkError("the network has no end hub")
        return self._end

    @property
    def zones(self) -> tuple[Zone, ...]:
        """Return every zone in declaration order."""
        return tuple(self._zones.values())

    @property
    def connections(self) -> tuple[Connection, ...]:
        """Return every connection in declaration order."""
        return tuple(self._connections.values())

    def has_zone(self, name: str) -> bool:
        """Return ``True`` when a zone named ``name`` exists."""
        return name in self._zones

    def zone(self, name: str) -> Zone:
        """Return the zone named ``name``.

        Raises:
            NetworkError: If the zone is unknown.
        """
        try:
            return self._zones[name]
        except KeyError:
            raise NetworkError(f"unknown zone {name!r}") from None

    def add_zone(self, zone: Zone) -> None:
        """Register a new zone.

        Raises:
            NetworkError: On duplicate names or duplicate start/end hubs.
        """
        if zone.name in self._zones:
            raise NetworkError(f"duplicate zone name {zone.name!r}")
        if zone.is_start and self._start is not None:
            raise NetworkError("more than one start_hub declared")
        if zone.is_end and self._end is not None:
            raise NetworkError("more than one end_hub declared")
        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []
        if zone.is_start:
            self._start = zone
        elif zone.is_end:
            self._end = zone

    def has_connection(self, first: str, second: str) -> bool:
        """Return ``True`` when the two zones are already linked."""
        return frozenset((first, second)) in self._connections

    def add_connection(self, connection: Connection) -> None:
        """Register a new connection.

        Raises:
            NetworkError: On unknown endpoints, self loops or duplicates.
        """
        first, second = connection.endpoints()
        for endpoint in (first, second):
            if endpoint not in self._zones:
                raise NetworkError(
                    f"connection {connection.name!r} refers to the "
                    f"undefined zone {endpoint!r}"
                )
        if first == second:
            raise NetworkError(
                f"connection {connection.name!r} links a zone to itself"
            )
        if connection.key in self._connections:
            raise NetworkError(
                f"connection {connection.name!r} is already defined"
            )
        self._connections[connection.key] = connection
        self._adjacency[first].append(second)
        self._adjacency[second].append(first)

    def neighbours(self, name: str) -> tuple[str, ...]:
        """Return the names of the zones adjacent to ``name``.

        Raises:
            NetworkError: If the zone is unknown.
        """
        if name not in self._adjacency:
            raise NetworkError(f"unknown zone {name!r}")
        return tuple(self._adjacency[name])

    def connection(self, first: str, second: str) -> Connection:
        """Return the connection linking the two zones.

        Raises:
            NetworkError: If the two zones are not linked.
        """
        key = frozenset((first, second))
        try:
            return self._connections[key]
        except KeyError:
            raise NetworkError(
                f"no connection between {first!r} and {second!r}"
            ) from None

    def path_cost(self, path: tuple[str, ...]) -> int:
        """Return the total turn cost of walking ``path``.

        The cost of a path is the sum of the entry costs of every zone
        after the first one, because staying in the start hub is free.
        """
        return sum(self.zone(name).move_cost for name in path[1:])

    def __repr__(self) -> str:
        """Return a debug representation of the network."""
        return (
            f"Network(zones={len(self._zones)}, "
            f"connections={len(self._connections)}, "
            f"nb_drones={self._nb_drones})"
        )
