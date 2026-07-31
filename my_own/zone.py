from enum import Enum


class ZoneType(Enum):
    """Behavioural category of a zone, driving entry cost and access."""

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
    """Role of a zone inside the drone network."""

    START = "start_hub"
    END = "end_hub"
    REGULAR = "hub"