"""Single drone shortest path search.

Movement cost is paid on *entering* a zone, so a path's cost is the sum
of the entry costs of every zone after the start hub.

``priority`` zones cost one turn like normal zones but must be preferred.
Preference is encoded without ever distorting the turn count: every cost
is scaled by ``weight = number_of_zones + 1`` and a priority zone gets a
single unit rebate. Because a simple path visits at most
``number_of_zones`` zones, the accumulated rebates of a whole path are
strictly smaller than one scaled turn, so a slower path can never look
cheaper than a faster one. The rebate only breaks ties.
"""

import heapq

from errors import NoRouteError
from network import Network


class ShortestPathFinder:
    """Dijkstra search over the zone network."""

    def __init__(self, network: Network) -> None:
        """Bind the finder to a network and precompute the scale factor."""
        self._network = network
        self._scale = len(network.zones) + 1

    @property
    def scale(self) -> int:
        """Return the factor used to scale turn costs."""
        return self._scale

    def entry_weight(self, zone_name: str) -> int:
        """Return the scaled, priority-adjusted cost of entering a zone."""
        zone = self._network.zone(zone_name)
        weight = zone.move_cost * self._scale
        if zone.zone_type.is_preferred:
            weight -= 1
        return weight

    def best_path(self) -> tuple[str, ...]:
        """Return the cheapest start-to-end path.

        Returns:
            The zone names from the start hub to the end hub, inclusive.

        Raises:
            NoRouteError: If the end hub is unreachable.
        """
        start = self._network.start.name
        end = self._network.end.name
        if not self._network.start.is_passable:
            raise NoRouteError("the start hub is blocked")
        if not self._network.end.is_passable:
            raise NoRouteError("the end hub is blocked")
        distance: dict[str, int] = {start: 0}
        previous: dict[str, str] = {}
        settled: set[str] = set()
        heap: list[tuple[int, str]] = [(0, start)]
        while heap:
            cost, name = heapq.heappop(heap)
            if name in settled:
                continue
            settled.add(name)
            if name == end:
                return self._rebuild(previous, start, end)
            for neighbour in self._network.neighbours(name):
                if neighbour in settled:
                    continue
                if not self._network.zone(neighbour).is_passable:
                    continue
                candidate = cost + self.entry_weight(neighbour)
                if candidate < distance.get(neighbour, candidate + 1):
                    distance[neighbour] = candidate
                    previous[neighbour] = name
                    heapq.heappush(heap, (candidate, neighbour))
        raise NoRouteError(
            f"no route from {start!r} to {end!r} avoiding blocked zones"
        )

    @staticmethod
    def _rebuild(
        previous: dict[str, str],
        start: str,
        end: str,
    ) -> tuple[str, ...]:
        """Walk the predecessor map backwards into a forward path."""
        path = [end]
        current = end
        while current != start:
            current = previous[current]
            path.append(current)
        path.reverse()
        return tuple(path)
