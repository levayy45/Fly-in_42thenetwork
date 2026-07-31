from enum import Enum


class ZoneType(Enum):
    NORMAL: str = "normal"
    BLOCKED: str = "blocked"
    RESTRICTED: str = "restricted"
    PRIORITY: str = "priority"

    @classmethod
    def from_text(cls, text: str) -> "ZoneType":
        """
        Convert a raw metadata value into a : class: 'ZoneType'.

        Args:
            text: the value found after 'Zone=' in metadata block.

        Returns:
            The matching enum member.

        Raises:
            ValueError: If 'text' is not a know zone type.
        """
        for member in cls:
            if member.value == text:
                return member
        allowed = ", ".join(member.value for member in cls)
        raise ValueError(
            f"Unknow zone type {text!r} (expected one of: {allowed})"
        )