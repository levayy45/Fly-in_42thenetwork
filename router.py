"""Route planning: choosing how many routes to use and who flies where.

Strategy, in three steps.

1. Model the network as a flow network. Each zone is split into an *in*
   node and an *out* node joined by an arc whose capacity is the zone's
   ``max_drones``; that is how a vertex capacity is expressed in an
   edge-capacitated flow problem. Each connection becomes one arc per
   direction with capacity ``max_link_capacity``.
2. Augment the flow one unit at a time with a minimum cost search. After
   each augmentation the flow decomposes into a set of routes that are
   guaranteed, by construction, to respect every zone and link capacity
   when used simultaneously. Because the search minimises cost, the set
   of ``k`` routes obtained is the cheapest such set.
3. For each candidate set, spread the fleet over the routes and keep the
   estimated completion time. Adding routes helps up to a point and then
   hurts, so every candidate is kept and the simulator picks the winner.
"""

from errors import NoRouteError
from flow import MinCostFlow
from network import Network
from pathfinder import ShortestPathFinder


class RoutePlan:
    """One candidate solution: a route per drone."""

    def __init__(
        self,
        routes: tuple[tuple[str, ...], ...],
        loads: tuple[int, ...],
        costs: tuple[int, ...],
    ) -> None:
        """Create a plan.

        Args:
            routes: The distinct routes actually used.
            loads: Number of drones assigned to each route.
            costs: Turn cost of each route.
        """
        self._routes = routes
        self._loads = loads
        self._costs = costs

    @property
    def routes(self) -> tuple[tuple[str, ...], ...]:
        """Return the distinct routes used by this plan."""
        return self._routes

    @property
    def loads(self) -> tuple[int, ...]:
        """Return the number of drones assigned to each route."""
        return self._loads

    @property
    def costs(self) -> tuple[int, ...]:
        """Return the turn cost of each route."""
        return self._costs

    @property
    def width(self) -> int:
        """Return how many routes the plan uses."""
        return len(self._routes)

    @property
    def estimate(self) -> int:
        """Return the predicted number of turns.

        A route of cost ``c`` fed one drone per turn delivers its ``d``
        drones after ``c + d - 1`` turns; the fleet finishes when the
        slowest route finishes.
        """
        if not self._routes:
            return 0
        return max(
            cost + load - 1
            for cost, load in zip(self._costs, self._loads)
            if load > 0
        )

    def drone_routes(self) -> tuple[tuple[str, ...], ...]:
        """Return one route per drone, interleaved across the routes.

        Interleaving matters: drone 1 takes the fastest route, drone 2
        the next best and so on, which is what keeps every route busy
        from the very first turn.
        """
        pending = list(self._loads)
        elapsed = list(self._costs)
        assigned: list[tuple[str, ...]] = []
        total = sum(self._loads)
        for _ in range(total):
            best = -1
            best_key = 0
            for index, remaining in enumerate(pending):
                if remaining <= 0:
                    continue
                key = elapsed[index]
                if best < 0 or key < best_key:
                    best = index
                    best_key = key
            if best < 0:
                break
            pending[best] -= 1
            elapsed[best] += 1
            assigned.append(self._routes[best])
        return tuple(assigned)

    def __repr__(self) -> str:
        """Return a debug representation of the plan."""
        return (
            f"RoutePlan(width={self.width}, loads={self._loads}, "
            f"costs={self._costs}, estimate={self.estimate})"
        )


class Router:
    """Build the candidate route plans for a network."""

    def __init__(self, network: Network) -> None:
        """Bind the router to a network and index its zones."""
        self._network = network
        self._finder = ShortestPathFinder(network)
        self._order = [zone.name for zone in network.zones]
        self._index = {name: pos for pos, name in enumerate(self._order)}

    @property
    def finder(self) -> ShortestPathFinder:
        """Return the shortest path helper used for cost weighting."""
        return self._finder

    def candidate_plans(self) -> tuple[RoutePlan, ...]:
        """Return every candidate plan, cheapest estimate first.

        Raises:
            NoRouteError: If the end hub cannot be reached at all.
        """
        fleet = self._network.nb_drones
        if fleet <= 0:
            return ()
        # Fails early with a clear message on blocked or disconnected maps.
        self._finder.best_path()
        graph, source, sink = self._build_graph()
        plans: list[RoutePlan] = []
        for _ in range(fleet):
            if graph.augment(source, sink, 1) == 0:
                break
            routes = self._decompose(graph, source, sink)
            if not routes:
                break
            plans.append(self._distribute(routes, fleet))
        if not plans:
            raise NoRouteError(
                "the end hub is unreachable under the capacity constraints"
            )
        return tuple(sorted(plans, key=lambda plan: plan.estimate))

    def _build_graph(self) -> tuple[MinCostFlow, int, int]:
        """Build the split-node flow network."""
        graph = MinCostFlow(2 * len(self._order))
        fleet = self._network.nb_drones
        for name in self._order:
            zone = self._network.zone(name)
            if not zone.is_passable:
                continue
            limit = zone.capacity
            capacity = fleet if limit is None else min(limit, fleet)
            graph.add_edge(
                self._in_node(name), self._out_node(name), capacity, 0
            )
        for connection in self._network.connections:
            first, second = connection.endpoints()
            if not self._network.zone(first).is_passable:
                continue
            if not self._network.zone(second).is_passable:
                continue
            capacity = min(connection.capacity, fleet)
            graph.add_edge(
                self._out_node(first),
                self._in_node(second),
                capacity,
                self._finder.entry_weight(second),
            )
            graph.add_edge(
                self._out_node(second),
                self._in_node(first),
                capacity,
                self._finder.entry_weight(first),
            )
        source = self._out_node(self._network.start.name)
        sink = self._in_node(self._network.end.name)
        return (graph, source, sink)

    def _in_node(self, name: str) -> int:
        """Return the index of a zone's entry node."""
        return 2 * self._index[name]

    def _out_node(self, name: str) -> int:
        """Return the index of a zone's exit node."""
        return 2 * self._index[name] + 1

    def _decompose(
        self,
        graph: MinCostFlow,
        source: int,
        sink: int,
    ) -> tuple[tuple[str, ...], ...]:
        """Split the current flow into concrete zone-name routes."""
        remaining = graph.flow_snapshot()
        routes: list[tuple[str, ...]] = []
        limit = graph.size * graph.size + 1
        while True:
            route = self._walk(graph, remaining, source, sink, limit)
            if route is None:
                break
            routes.append(route)
        return tuple(routes)

    def _walk(
        self,
        graph: MinCostFlow,
        remaining: list[list[int]],
        source: int,
        sink: int,
        limit: int,
    ) -> tuple[str, ...] | None:
        """Follow one unit of flow from source to sink, consuming it."""
        node = source
        names = [self._network.start.name]
        steps = 0
        while node != sink:
            steps += 1
            if steps > limit:
                return None
            moved = False
            for index, edge in enumerate(graph.outgoing(node)):
                if remaining[node][index] <= 0:
                    continue
                remaining[node][index] -= 1
                node = edge.target
                if node % 2 == 0:
                    names.append(self._order[node // 2])
                moved = True
                break
            if not moved:
                return None
        return tuple(names)

    def _distribute(
        self,
        routes: tuple[tuple[str, ...], ...],
        fleet: int,
    ) -> RoutePlan:
        """Spread ``fleet`` drones over ``routes`` to finish earliest."""
        costs = [self._network.path_cost(route) for route in routes]
        loads = [0] * len(routes)
        for _ in range(fleet):
            best = 0
            best_key = costs[0] + loads[0]
            for index in range(1, len(routes)):
                key = costs[index] + loads[index]
                if key < best_key:
                    best = index
                    best_key = key
            loads[best] += 1
        used = [index for index, load in enumerate(loads) if load > 0]
        return RoutePlan(
            routes=tuple(routes[index] for index in used),
            loads=tuple(loads[index] for index in used),
            costs=tuple(costs[index] for index in used),
        )
