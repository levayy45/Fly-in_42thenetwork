class FlyInError(Exception):
    """Base class of every error this project raises."""


class NetworkError(FlyInError):
    """Raised when the zone network is built or queried incorrectly."""


class ParseError(FlyInError):
    pass
