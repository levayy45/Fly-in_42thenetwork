"""The turn engine: the single authority on what is a legal move.

The router only *proposes* routes. This module executes them turn by turn
and enforces every rule of the subject:

* a zone holds at most ``max_drones`` drones, the start and end hubs
  being unlimited;
* a connection carries at most ``max_link_capacity`` drones at once;
* a drone leaving a zone frees its slot during the same turn, which is
  why drones are processed from the closest to the goal to the furthest;
* a drone crossing towards a ``restricted`` zone spends the extra turns
  on the connection and *must* land on schedule, so its landing slot is
  reserved in advance and no other drone can steal it.

If a plan cannot progress the engine raises instead of looping forever,
so a bad plan is rejected rather than silently producing junk output.
"""

from collections import Counter

from drone import Drone
from errors import SimulationError
from network import Network
from router import RoutePlan


class TurnRecord:
    """The movements performed during one simulation turn."""

    def __init__(self, number: int, moves: tuple[str, ...]) -> None:
        """Store the turn number and its ordered movement tokens."""
        self._number = number
        self._moves = moves

    @property
    def number(self) -> int:
        """Return the 1-based turn number."""
        return self._number

    @property
    def moves(self) -> tuple[str, ...]:
        """Return the movement tokens, e.g. ``('D1-roof1',)``."""
        return self._moves

    def render(self) -> str:
        """Return the line printed for this turn."""
        return " ".join(self._moves)

    def __repr__(self) -> str:
        """Return a debug representation of the turn."""
        return f"TurnRecord({self._number}, {self._moves!r})"


class SimulationResult:
    """The outcome of running one plan to completion."""

    def __init__(
        self,
        plan: RoutePlan,
        records: tuple[TurnRecord, ...],
        drones: tuple[Drone, ...],
        network: Network,
    ) -> None:
        """Bundle the plan, its turn log and the final drone states."""
        self._plan = plan
        self._records = records
        self._drones = drones
        self._network = network

    @property
    def plan(self) -> RoutePlan:
        """Return the plan that produced this result."""
        return self._plan

    @property
    def records(self) -> tuple[TurnRecord, ...]:
        """Return the per-turn movement log."""
        return self._records

    @property
    def drones(self) -> tuple[Drone, ...]:
        """Return the drones in identifier order."""
        return self._drones

    @property
    def turns(self) -> int:
        """Return the total number of simulation turns used."""
        return len(self._records)

    @property
    def total_moves(self) -> int:
        """Return how many individual movements were performed."""
        return sum(len(record.moves) for record in self._records)

    @property
    def moves_per_turn(self) -> float:
        """Return the average number of movements per turn."""
        if not self._records:
            return 0.0
        return self.total_moves / len(self._records)

    @property
    def average_turns_per_drone(self) -> float:
        """Return the average delivery turn across the fleet."""
        if not self._drones:
            return 0.0
        return sum(d.delivery_turn for d in self._drones) / len(self._drones)

    @property
    def total_path_cost(self) -> int:
        """Return the summed weighted route cost of the whole fleet."""
        return sum(
            self._network.path_cost(drone.route) for drone in self._drones
        )

    def render(self) -> str:
        """Return the whole simulation in the mandated output format."""
        return "\n".join(record.render() for record in self._records)


class Simulator:
    """Execute a :class:`~router.RoutePlan` under every movement rule."""

    def __init__(self, network: Network) -> None:
        """Bind the simulator to a network."""
        self._network = network

    def run(self, plan: RoutePlan) -> SimulationResult:
        """Run ``plan`` until every drone is delivered.

        Args:
            plan: The candidate plan to execute.

        Returns:
            The full simulation result.

        Raises:
            SimulationError: If the plan deadlocks or overruns the safety
                turn budget.
        """
        drones = self._spawn(plan)
        occupancy: Counter[str] = Counter()
        reserved: Counter[str] = Counter()
        records: list[TurnRecord] = []
        budget = self._turn_budget(drones)
        turn = 0
        while any(not drone.is_delivered for drone in drones):
            turn += 1
            if turn > budget:
                raise SimulationError(
                    f"the plan did not finish within {budget} turns"
                )
            moves = self._run_turn(turn, drones, occupancy, reserved)
            if not moves:
                raise SimulationError(
                    f"deadlock on turn {turn}: no drone can move"
                )
            records.append(TurnRecord(turn, tuple(moves)))
        return SimulationResult(
            plan, tuple(records), drones, self._network
        )

    def _spawn(self, plan: RoutePlan) -> tuple[Drone, ...]:
        """Create the fleet, one drone per assigned route."""
        routes = plan.drone_routes()
        if len(routes) != self._network.nb_drones:
            raise SimulationError(
                "the plan does not cover every drone "
                f"({len(routes)} routes for {self._network.nb_drones} "
                "drones)"
            )
        return tuple(
            Drone(number, route)
            for number, route in enumerate(routes, start=1)
        )

    def _turn_budget(self, drones: tuple[Drone, ...]) -> int:
        """Return a generous upper bound on the number of turns."""
        longest = max(
            (self._network.path_cost(drone.route) for drone in drones),
            default=1,
        )
        return longest + len(drones) * (longest + 2) + 10

    def _run_turn(
        self,
        turn: int,
        drones: tuple[Drone, ...],
        occupancy: Counter[str],
        reserved: Counter[str],
    ) -> list[str]:
        """Execute one turn and return its movement tokens.

        Tokens come back sorted by drone number so the output line is
        stable and easy to read, whatever order the engine picked to
        resolve the movements internally.
        """
        moves: list[tuple[int, str]] = []
        links: Counter[frozenset[str]] = Counter()
        # Both groups are snapshotted before anything moves: a drone that
        # lands this turn has already used its single movement and must
        # not be offered a second one.
        flying = [drone for drone in drones if drone.is_in_flight]
        grounded = [
            drone
            for drone in drones
            if not drone.is_delivered and not drone.is_in_flight
        ]
        for drone in flying:
            link = self._network.connection(
                drone.origin_name, drone.route[drone.position + 1]
            )
            links[link.key] += 1
        for drone in self._by_urgency(flying):
            token = self._advance_flight(turn, drone, occupancy, reserved)
            moves.append((drone.identifier, token))
        for drone in self._by_urgency(grounded):
            moved = self._try_move(turn, drone, occupancy, reserved, links)
            if moved is not None:
                moves.append((drone.identifier, moved))
        moves.sort()
        return [token for _, token in moves]

    def _by_urgency(self, drones: list[Drone]) -> list[Drone]:
        """Order drones from the closest to the goal to the furthest.

        Letting the leaders move first is what makes the rule "a drone
        leaving a zone frees its slot during the same turn" usable: the
        drone behind sees the freed slot in the very same turn.
        """
        return sorted(drones, key=self._remaining_cost)

    def _remaining_cost(self, drone: Drone) -> int:
        """Return the turn cost left before the drone is delivered."""
        return self._network.path_cost(drone.route[drone.position:])

    def _advance_flight(
        self,
        turn: int,
        drone: Drone,
        occupancy: Counter[str],
        reserved: Counter[str],
    ) -> str:
        """Advance one in-flight drone and return its movement token."""
        origin = drone.origin_name
        target = drone.route[drone.position + 1]
        link = self._network.connection(origin, target)
        if not drone.continue_flight():
            return f"{drone.label}-{link.name}"
        reserved[target] -= 1
        self._land(turn, drone, target, occupancy)
        return f"{drone.label}-{target}"

    def _try_move(
        self,
        turn: int,
        drone: Drone,
        occupancy: Counter[str],
        reserved: Counter[str],
        links: Counter[frozenset[str]],
    ) -> str | None:
        """Try to move a grounded drone, returning its token on success."""
        origin = drone.zone_name
        target = drone.target_name
        zone = self._network.zone(target)
        link = self._network.connection(origin, target)
        if links[link.key] >= link.capacity:
            return None
        if not zone.accepts(occupancy[target] + reserved[target]):
            return None
        occupancy[origin] -= 1
        links[link.key] += 1
        if zone.move_cost == 1:
            drone.step()
            self._land(turn, drone, target, occupancy)
            return f"{drone.label}-{target}"
        reserved[target] += 1
        drone.begin_flight(zone.move_cost - 1)
        return f"{drone.label}-{link.name}"

    def _land(
        self,
        turn: int,
        drone: Drone,
        target: str,
        occupancy: Counter[str],
    ) -> None:
        """Register a drone that just entered ``target``."""
        if self._network.zone(target).is_end:
            drone.mark_delivered(turn)
            return
        occupancy[target] += 1


class PlanSelector:
    """Simulate every candidate plan and keep the fastest valid one."""

    def __init__(self, network: Network) -> None:
        """Bind the selector to a network."""
        self._network = network
        self._simulator = Simulator(network)
        self._failures: list[str] = []

    @property
    def failures(self) -> tuple[str, ...]:
        """Return the reason each rejected plan was discarded."""
        return tuple(self._failures)

    def best(self, plans: tuple[RoutePlan, ...]) -> SimulationResult:
        """Return the result with the lowest turn count.

        Args:
            plans: Candidate plans, typically from
                :meth:`~router.Router.candidate_plans`.

        Returns:
            The best valid simulation result.

        Raises:
            SimulationError: If no candidate plan can be executed.
        """
        self._failures = []
        best: SimulationResult | None = None
        for plan in plans:
            try:
                result = self._simulator.run(plan)
            except SimulationError as error:
                self._failures.append(f"width {plan.width}: {error}")
                continue
            if best is None or result.turns < best.turns:
                best = result
        if best is None:
            detail = "; ".join(self._failures) or "no candidate plan"
            raise SimulationError(f"no plan could be executed ({detail})")
        return best
