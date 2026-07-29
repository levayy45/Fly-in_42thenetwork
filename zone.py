"""Zone modelling: zone types, zone roles and the :class:`Zone` entity."""

from enum import Enum


class ZoneType(Enum):
    """Behavioural category of a zone.

    The category drives the movement cost paid to *enter* the zone and
    whether the zone can be entered at all.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @classmethod
    def from_text(cls, text: str) -> "ZoneType":
        """Convert a raw metadata value into a :class:`ZoneType`.

        Args:
            text: The value found after ``zone=`` in a metadata block.

        Returns:
            The matching enum member.

        Raises:
            ValueError: If ``text`` is not a known zone type.
        """
        for member in cls:
            if member.value == text:
                return member
        allowed = ", ".join(member.value for member in cls)
        raise ValueError(
            f"unknown zone type {text!r} (expected one of: {allowed})"
        )

    @property
    def move_cost(self) -> int:
        """Return the number of turns needed to enter this kind of zone."""
        if self is ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def is_passable(self) -> bool:
        """Return ``True`` when drones are allowed inside this zone."""
        return self is not ZoneType.BLOCKED

    @property
    def is_preferred(self) -> bool:
        """Return ``True`` for zones pathfinding should favour."""
        return self is ZoneType.PRIORITY


class ZoneRole(Enum):
    """Role of a zone inside the network."""

    START = "start_hub"
    END = "end_hub"
    REGULAR = "hub"


class Zone:
    """A single node of the drone network.

    Capacity semantics follow the subject: a regular zone holds at most
    ``max_drones`` drones at once, while the start and end hubs are
    unlimited and ignore any declared capacity.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        role: ZoneRole,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: str | None = None,
        max_drones: int = 1,
    ) -> None:
        """Create a zone.

        Args:
            name: Unique zone identifier.
            x: Integer x coordinate.
            y: Integer y coordinate.
            role: Whether the zone is the start, the end or a regular hub.
            zone_type: Behavioural category of the zone.
            color: Optional display colour.
            max_drones: Declared simultaneous occupancy limit.
        """
        self._name = name
        self._x = x
        self._y = y
        self._role = role
        self._zone_type = zone_type
        self._color = color
        self._max_drones = max_drones

    @property
    def name(self) -> str:
        """Return the zone name."""
        return self._name

    @property
    def x(self) -> int:
        """Return the x coordinate."""
        return self._x

    @property
    def y(self) -> int:
        """Return the y coordinate."""
        return self._y

    @property
    def role(self) -> ZoneRole:
        """Return the role of the zone in the network."""
        return self._role

    @property
    def zone_type(self) -> ZoneType:
        """Return the behavioural category of the zone."""
        return self._zone_type

    @property
    def color(self) -> str | None:
        """Return the declared display colour, if any."""
        return self._color

    @property
    def is_start(self) -> bool:
        """Return ``True`` when this zone is the start hub."""
        return self._role is ZoneRole.START

    @property
    def is_end(self) -> bool:
        """Return ``True`` when this zone is the end hub."""
        return self._role is ZoneRole.END

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` for the start and end hubs."""
        return self.is_start or self.is_end

    @property
    def is_passable(self) -> bool:
        """Return ``True`` when drones may enter this zone."""
        return self._zone_type.is_passable

    @property
    def move_cost(self) -> int:
        """Return the turn cost paid to enter this zone."""
        return self._zone_type.move_cost

    @property
    def capacity(self) -> int | None:
        """Return the occupancy limit, or ``None`` when unlimited."""
        if self.is_terminal:
            return None
        return self._max_drones

    @property
    def declared_capacity(self) -> int:
        """Return the raw ``max_drones`` value read from the file."""
        return self._max_drones

    def accepts(self, occupants: int) -> bool:
        """Return ``True`` if one more drone fits given current occupants.

        Args:
            occupants: Number of drones already counted inside the zone.
        """
        if not self.is_passable:
            return False
        limit = self.capacity
        if limit is None:
            return True
        return occupants < limit

    def __repr__(self) -> str:
        """Return a debug representation of the zone."""
        return (
            f"Zone(name={self._name!r}, type={self._zone_type.value!r}, "
            f"role={self._role.value!r}, capacity={self.capacity})"
        )
