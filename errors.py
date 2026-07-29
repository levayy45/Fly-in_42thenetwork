"""Exception hierarchy used by the Fly-in drone routing project.

Every recoverable failure raises a subclass of :class:`FlyInError` so the
entry point can catch a single base type and exit cleanly instead of
letting a traceback escape.
"""


class FlyInError(Exception):
    """Base class of every error raised by this project."""


class ParseError(FlyInError):
    """Raised when a map file violates the expected structure or syntax.

    Attributes:
        line_number: 1-based index of the offending line in the file.
        line: Raw text of the offending line.
        reason: Human readable explanation of the problem.
    """

    def __init__(self, line_number: int, line: str, reason: str) -> None:
        """Store the location and the cause of the parsing failure."""
        self._line_number = line_number
        self._line = line
        self._reason = reason
        super().__init__(self.describe())

    @property
    def line_number(self) -> int:
        """Return the 1-based line number that failed to parse."""
        return self._line_number

    @property
    def line(self) -> str:
        """Return the raw offending line."""
        return self._line

    @property
    def reason(self) -> str:
        """Return the explanation of the failure."""
        return self._reason

    def describe(self) -> str:
        """Build the message shown to the user."""
        stripped = self._line.strip()
        if stripped:
            return (
                f"parse error on line {self._line_number}: {self._reason}"
                f"\n  >>> {stripped}"
            )
        return f"parse error on line {self._line_number}: {self._reason}"


class NetworkError(FlyInError):
    """Raised when the zone network is queried in an invalid way."""


class NoRouteError(FlyInError):
    """Raised when no valid route exists between the start and end zones."""


class SimulationError(FlyInError):
    """Raised when a plan cannot be executed (deadlock, capacity clash)."""
