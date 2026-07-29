"""A hand written min-cost max-flow solver.

The router needs, for every fleet size ``k``, the *cheapest* set of ``k``
simultaneously usable routes. That is exactly a minimum cost flow of
value ``k``, so this module implements the successive shortest path
algorithm with a queue based Bellman-Ford (SPFA) shortest path search.
SPFA is required rather than Dijkstra because residual arcs carry
negative costs.

Nothing here knows about drones or zones: it is a plain integer graph.
"""

from collections import deque

INFINITY = float("inf")


class FlowEdge:
    """One directed arc of the residual graph."""

    __slots__ = ("target", "capacity", "cost", "reverse", "original")

    def __init__(
        self,
        target: int,
        capacity: int,
        cost: int,
        reverse: int,
        original: int,
    ) -> None:
        """Create a residual arc.

        Args:
            target: Index of the head node.
            capacity: Remaining capacity of the arc.
            cost: Cost per unit of flow.
            reverse: Index of the paired arc inside ``target``'s list.
            original: Capacity the arc was created with.
        """
        self.target = target
        self.capacity = capacity
        self.cost = cost
        self.reverse = reverse
        self.original = original

    @property
    def flow(self) -> int:
        """Return how much flow currently crosses this arc."""
        return self.original - self.capacity

    def __repr__(self) -> str:
        """Return a debug representation of the arc."""
        return (
            f"FlowEdge(target={self.target}, capacity={self.capacity}, "
            f"cost={self.cost})"
        )


class MinCostFlow:
    """Residual graph supporting incremental minimum cost augmentation."""

    def __init__(self, size: int) -> None:
        """Create a graph with ``size`` nodes and no arcs."""
        self._size = size
        self._graph: list[list[FlowEdge]] = [[] for _ in range(size)]

    @property
    def size(self) -> int:
        """Return the number of nodes."""
        return self._size

    def add_edge(
        self,
        source: int,
        target: int,
        capacity: int,
        cost: int,
    ) -> None:
        """Add a directed arc and its zero capacity residual twin."""
        forward = FlowEdge(
            target, capacity, cost, len(self._graph[target]), capacity
        )
        backward = FlowEdge(
            source, 0, -cost, len(self._graph[source]), 0
        )
        self._graph[source].append(forward)
        self._graph[target].append(backward)

    def outgoing(self, node: int) -> list[FlowEdge]:
        """Return the arcs leaving ``node``."""
        return self._graph[node]

    def augment(self, source: int, sink: int, units: int) -> int:
        """Push at most ``units`` of flow along the cheapest path.

        Args:
            source: Index of the source node.
            sink: Index of the sink node.
            units: Upper bound on the amount of flow to push.

        Returns:
            The amount of flow actually pushed, ``0`` when the sink is
            no longer reachable.
        """
        if units <= 0:
            return 0
        distance, previous_node, previous_edge = self._shortest_path(
            source, sink
        )
        if distance[sink] == INFINITY:
            return 0
        pushed = self._bottleneck(
            source, sink, units, previous_node, previous_edge
        )
        self._apply(source, sink, pushed, previous_node, previous_edge)
        return pushed

    def _shortest_path(
        self,
        source: int,
        sink: int,
    ) -> tuple[list[float], list[int], list[int]]:
        """Run SPFA and return distances plus the predecessor arrays."""
        distance: list[float] = [INFINITY] * self._size
        previous_node = [-1] * self._size
        previous_edge = [-1] * self._size
        queued = [False] * self._size
        distance[source] = 0
        pending: deque[int] = deque([source])
        queued[source] = True
        while pending:
            node = pending.popleft()
            queued[node] = False
            base = distance[node]
            for index, edge in enumerate(self._graph[node]):
                if edge.capacity <= 0:
                    continue
                candidate = base + edge.cost
                if candidate < distance[edge.target]:
                    distance[edge.target] = candidate
                    previous_node[edge.target] = node
                    previous_edge[edge.target] = index
                    if not queued[edge.target]:
                        queued[edge.target] = True
                        pending.append(edge.target)
        del sink
        return (distance, previous_node, previous_edge)

    def _bottleneck(
        self,
        source: int,
        sink: int,
        units: int,
        previous_node: list[int],
        previous_edge: list[int],
    ) -> int:
        """Return the largest amount of flow the found path accepts."""
        available = units
        node = sink
        while node != source:
            edge = self._graph[previous_node[node]][previous_edge[node]]
            available = min(available, edge.capacity)
            node = previous_node[node]
        return available

    def _apply(
        self,
        source: int,
        sink: int,
        pushed: int,
        previous_node: list[int],
        previous_edge: list[int],
    ) -> None:
        """Update the residual capacities along the found path."""
        node = sink
        while node != source:
            edge = self._graph[previous_node[node]][previous_edge[node]]
            edge.capacity -= pushed
            self._graph[node][edge.reverse].capacity += pushed
            node = previous_node[node]

    def flow_snapshot(self) -> list[list[int]]:
        """Return the current flow of every arc, indexed like the graph."""
        return [
            [edge.flow for edge in edges] for edges in self._graph
        ]
