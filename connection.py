"""Connection modelling: a bidirectional edge between two zones."""

from errors import NetworkError


class Connection:
    """A bidirectional link between two zones.

    A connection is identified by the *unordered* pair of zone names, so
    ``a-b`` and ``b-a`` describe the same object. The textual name keeps
    the orientation found in the map file because the simulation output
    must print connection names for drones in flight.
    """

    def __init__(
        self,
        first: str,
        second: str,
        capacity: int = 1,
    ) -> None:
        """Create a connection.

        Args:
            first: Name of the first endpoint, as written in the file.
            second: Name of the second endpoint, as written in the file.
            capacity: Maximum number of drones crossing it at once.
        """
        self._first = first
        self._second = second
        self._capacity = capacity

    @property
    def first(self) -> str:
        """Return the first endpoint name."""
        return self._first

    @property
    def second(self) -> str:
        """Return the second endpoint name."""
        return self._second

    @property
    def capacity(self) -> int:
        """Return the ``max_link_capacity`` of the connection."""
        return self._capacity

    @property
    def name(self) -> str:
        """Return the printable name, e.g. ``corridorA-tunnelB``."""
        return f"{self._first}-{self._second}"

    @property
    def key(self) -> frozenset[str]:
        """Return the orientation independent identity of the link."""
        return frozenset((self._first, self._second))

    def endpoints(self) -> tuple[str, str]:
        """Return both endpoint names as a tuple."""
        return (self._first, self._second)

    def other(self, zone_name: str) -> str:
        """Return the endpoint opposite to ``zone_name``.

        Args:
            zone_name: One of the two endpoints.

        Raises:
            NetworkError: If ``zone_name`` is not an endpoint.
        """
        if zone_name == self._first:
            return self._second
        if zone_name == self._second:
            return self._first
        raise NetworkError(
            f"zone {zone_name!r} is not an endpoint of {self.name!r}"
        )

    def __repr__(self) -> str:
        """Return a debug representation of the connection."""
        return f"Connection({self.name!r}, capacity={self._capacity})"
