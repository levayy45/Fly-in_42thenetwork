"""The :class:`Drone` entity and its movement state machine.

A drone is always in exactly one of three states:

* ``AT_ZONE``   -- sitting inside a zone, free to move or to wait;
* ``IN_FLIGHT`` -- crossing a connection towards a multi-turn zone, and
  therefore committed to landing on schedule;
* ``DELIVERED`` -- inside the end hub and no longer tracked.
"""

from enum import Enum

from errors import SimulationError


class DroneState(Enum):
    """Lifecycle state of a drone."""

    AT_ZONE = "at_zone"
    IN_FLIGHT = "in_flight"
    DELIVERED = "delivered"


class Drone:
    """A single drone following a precomputed route."""

    def __init__(self, identifier: int, route: tuple[str, ...]) -> None:
        """Create a drone parked at the first zone of ``route``.

        Args:
            identifier: 1-based drone number used in the output.
            route: Zone names from the start hub to the end hub.

        Raises:
            SimulationError: If the route is too short to be flown.
        """
        if len(route) < 2:
            raise SimulationError(
                f"drone D{identifier} received a route with no destination"
            )
        self._identifier = identifier
        self._route = route
        self._position = 0
        self._state = DroneState.AT_ZONE
        self._flight_left = 0
        self._delivery_turn = 0

    @property
    def identifier(self) -> int:
        """Return the drone number."""
        return self._identifier

    @property
    def label(self) -> str:
        """Return the printable drone label, e.g. ``D3``."""
        return f"D{self._identifier}"

    @property
    def route(self) -> tuple[str, ...]:
        """Return the full route of the drone."""
        return self._route

    @property
    def state(self) -> DroneState:
        """Return the current lifecycle state."""
        return self._state

    @property
    def position(self) -> int:
        """Return the index of the current zone inside the route."""
        return self._position

    @property
    def zone_name(self) -> str:
        """Return the zone the drone occupies.

        Raises:
            SimulationError: If the drone is currently in flight.
        """
        if self._state is DroneState.IN_FLIGHT:
            raise SimulationError(
                f"{self.label} is in flight and occupies no zone"
            )
        return self._route[self._position]

    @property
    def origin_name(self) -> str:
        """Return the last zone the drone left or occupies."""
        return self._route[self._position]

    @property
    def target_name(self) -> str:
        """Return the next zone on the route.

        Raises:
            SimulationError: If the drone has no next zone.
        """
        if self._position + 1 >= len(self._route):
            raise SimulationError(f"{self.label} has no next zone")
        return self._route[self._position + 1]

    @property
    def is_delivered(self) -> bool:
        """Return ``True`` once the drone reached the end hub."""
        return self._state is DroneState.DELIVERED

    @property
    def is_in_flight(self) -> bool:
        """Return ``True`` while the drone occupies a connection."""
        return self._state is DroneState.IN_FLIGHT

    @property
    def delivery_turn(self) -> int:
        """Return the turn the drone landed, or ``0`` if still flying."""
        return self._delivery_turn

    def begin_flight(self, turns: int) -> None:
        """Leave the current zone for a multi-turn crossing.

        Args:
            turns: Number of turns spent on the connection before
                landing. Always ``cost - 1`` for the destination zone.

        Raises:
            SimulationError: If the drone is not free to move.
        """
        if self._state is not DroneState.AT_ZONE:
            raise SimulationError(f"{self.label} cannot start a flight now")
        if turns < 1:
            raise SimulationError(
                f"{self.label} was given a flight shorter than one turn"
            )
        self._state = DroneState.IN_FLIGHT
        self._flight_left = turns

    def continue_flight(self) -> bool:
        """Advance an in-flight drone by one turn.

        Returns:
            ``True`` when the drone landed on its destination this turn,
            ``False`` when it is still crossing the connection.

        Raises:
            SimulationError: If the drone is not in flight.
        """
        if self._state is not DroneState.IN_FLIGHT:
            raise SimulationError(f"{self.label} is not in flight")
        self._flight_left -= 1
        if self._flight_left > 0:
            return False
        self._state = DroneState.AT_ZONE
        self._position += 1
        return True

    def step(self) -> None:
        """Move the drone to the next zone in a single turn.

        Raises:
            SimulationError: If the drone is not free to move.
        """
        if self._state is not DroneState.AT_ZONE:
            raise SimulationError(f"{self.label} cannot step now")
        self._position += 1

    def mark_delivered(self, turn: int) -> None:
        """Flag the drone as delivered on ``turn``."""
        self._state = DroneState.DELIVERED
        self._delivery_turn = turn

    def has_arrived(self) -> bool:
        """Return ``True`` when the drone stands on the last route zone."""
        return self._position + 1 == len(self._route)

    def __repr__(self) -> str:
        """Return a debug representation of the drone."""
        return (
            f"Drone({self.label}, state={self._state.value!r}, "
            f"position={self._position})"
        )
