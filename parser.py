"""Parsing of map files into a :class:`~network.Network`.

The parser is deliberately strict: every violation of the format raises a
:class:`~errors.ParseError` carrying the line number and the cause, and no
partially built network is ever returned.
"""

from connection import Connection
from errors import NetworkError, ParseError
from metadata import Metadata, MetadataError
from network import Network
from zone import Zone, ZoneRole, ZoneType

ZONE_KEYS = frozenset({"zone", "color", "max_drones"})
LINK_KEYS = frozenset({"max_link_capacity"})
FORBIDDEN_NAME_CHARS = "-[]#=:"
DRONE_PREFIX = "nb_drones:"
ROLE_PREFIXES: dict[str, ZoneRole] = {
    "start_hub:": ZoneRole.START,
    "end_hub:": ZoneRole.END,
    "hub:": ZoneRole.REGULAR,
}
LINK_PREFIX = "connection:"


class MapParser:
    """Turn the textual map format into a validated network object."""

    def __init__(self) -> None:
        """Create a parser with no state carried between runs."""
        self._network: Network | None = None
        self._line_number = 0
        self._line = ""

    def parse_file(self, path: str) -> Network:
        """Read ``path`` and return the parsed network.

        Args:
            path: Filesystem path of the map file.

        Returns:
            The validated network.

        Raises:
            ParseError: On any syntax or consistency violation.
            OSError: If the file cannot be read.
        """
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> Network:
        """Parse an already loaded list of raw lines.

        Args:
            lines: The raw file content, one entry per line.

        Returns:
            The validated network.

        Raises:
            ParseError: On any syntax or consistency violation.
        """
        self._network = None
        for index, raw in enumerate(lines, start=1):
            self._line_number = index
            self._line = raw
            content = self._strip_comment(raw)
            if not content:
                continue
            self._consume(content)
        return self._finish(len(lines))

    @staticmethod
    def _strip_comment(raw: str) -> str:
        """Remove a trailing comment and surrounding whitespace."""
        head = raw.split("#", 1)[0]
        return head.strip()

    def _fail(self, reason: str) -> ParseError:
        """Build a :class:`ParseError` for the line being parsed."""
        return ParseError(self._line_number, self._line, reason)

    def _consume(self, content: str) -> None:
        """Dispatch one meaningful line to the right handler."""
        if self._network is None:
            self._read_fleet_size(content)
            return
        if content.startswith(DRONE_PREFIX):
            raise self._fail("nb_drones is declared more than once")
        for prefix, role in ROLE_PREFIXES.items():
            if content.startswith(prefix):
                self._read_zone(content[len(prefix):], role)
                return
        if content.startswith(LINK_PREFIX):
            self._read_connection(content[len(LINK_PREFIX):])
            return
        raise self._fail(
            "unrecognised line (expected start_hub:, end_hub:, hub: "
            "or connection:)"
        )

    def _read_fleet_size(self, content: str) -> None:
        """Parse the mandatory ``nb_drones:`` header line."""
        if not content.startswith(DRONE_PREFIX):
            raise self._fail(
                "the first meaningful line must be "
                "'nb_drones: <positive_integer>'"
            )
        raw = content[len(DRONE_PREFIX):].strip()
        if not raw:
            raise self._fail("nb_drones is missing its value")
        try:
            value = int(raw)
        except ValueError:
            raise self._fail(f"nb_drones value {raw!r} is not an integer")
        if value <= 0:
            raise self._fail("nb_drones must be a positive integer")
        self._network = Network(value)

    def _split_metadata(self, body: str) -> tuple[str, str | None]:
        """Split a line body into its head and its metadata block."""
        opening = body.find("[")
        if opening < 0:
            if "]" in body:
                raise self._fail("closing ']' without a matching '['")
            return (body.strip(), None)
        head = body[:opening]
        block = body[opening:]
        return (head.strip(), block)

    def _read_zone(self, body: str, role: ZoneRole) -> None:
        """Parse a ``start_hub:``, ``end_hub:`` or ``hub:`` line."""
        network = self._require_network()
        head, block = self._split_metadata(body)
        fields = head.split()
        if len(fields) != 3:
            raise self._fail(
                "zone declaration must be '<name> <x> <y> [metadata]'"
            )
        name = self._validate_name(fields[0])
        x = self._read_int(fields[1], "x coordinate")
        y = self._read_int(fields[2], "y coordinate")
        metadata = self._read_metadata(block, ZONE_KEYS)
        zone_type = self._read_zone_type(metadata)
        capacity = self._read_capacity(metadata, role)
        zone = Zone(
            name=name,
            x=x,
            y=y,
            role=role,
            zone_type=zone_type,
            color=metadata.optional_text("color"),
            max_drones=capacity,
        )
        try:
            network.add_zone(zone)
        except NetworkError as error:
            raise self._fail(str(error)) from None

    def _read_zone_type(self, metadata: Metadata) -> ZoneType:
        """Read and validate the ``zone=`` tag."""
        raw = metadata.text("zone", ZoneType.NORMAL.value)
        try:
            return ZoneType.from_text(raw)
        except ValueError as error:
            raise self._fail(str(error)) from None

    def _read_capacity(self, metadata: Metadata, role: ZoneRole) -> int:
        """Read ``max_drones``, ignoring it on the start and end hubs."""
        try:
            capacity = metadata.positive_int("max_drones", 1)
        except MetadataError as error:
            raise self._fail(str(error)) from None
        if role is not ZoneRole.REGULAR:
            return 1
        return capacity

    def _read_connection(self, body: str) -> None:
        """Parse a ``connection:`` line."""
        network = self._require_network()
        head, block = self._split_metadata(body)
        fields = head.split()
        if len(fields) != 1:
            raise self._fail(
                "connection must be '<zone1>-<zone2> [metadata]' with no "
                "spaces around the dash"
            )
        parts = fields[0].split("-")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise self._fail(
                "connection must name exactly two zones separated by '-'"
            )
        metadata = self._read_metadata(block, LINK_KEYS)
        try:
            capacity = metadata.positive_int("max_link_capacity", 1)
        except MetadataError as error:
            raise self._fail(str(error)) from None
        connection = Connection(parts[0], parts[1], capacity)
        try:
            network.add_connection(connection)
        except NetworkError as error:
            raise self._fail(str(error)) from None

    def _read_metadata(
        self,
        block: str | None,
        allowed: frozenset[str],
    ) -> Metadata:
        """Parse an optional metadata block."""
        if block is None:
            return Metadata.empty()
        try:
            return Metadata.parse(block, allowed)
        except MetadataError as error:
            raise self._fail(str(error)) from None

    def _validate_name(self, name: str) -> str:
        """Ensure a zone name uses only legal characters."""
        if not name:
            raise self._fail("zone name is empty")
        for char in name:
            if char.isspace() or char in FORBIDDEN_NAME_CHARS:
                raise self._fail(
                    f"zone name {name!r} contains the forbidden "
                    f"character {char!r}"
                )
        return name

    def _read_int(self, raw: str, label: str) -> int:
        """Parse an integer coordinate."""
        try:
            return int(raw)
        except ValueError:
            raise self._fail(f"{label} {raw!r} is not an integer") from None

    def _require_network(self) -> Network:
        """Return the network under construction."""
        if self._network is None:
            raise self._fail("nb_drones must be declared first")
        return self._network

    def _finish(self, total_lines: int) -> Network:
        """Run the whole-file checks and return the network."""
        self._line_number = max(total_lines, 1)
        self._line = ""
        if self._network is None:
            raise self._fail("the map file declares no nb_drones header")
        network = self._network
        try:
            start = network.start
            end = network.end
        except NetworkError as error:
            raise self._fail(str(error)) from None
        if start.name == end.name:
            raise self._fail("the start and end hubs must be distinct")
        return network
