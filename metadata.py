"""Parsing of the optional ``[key=value ...]`` metadata blocks."""


class MetadataError(ValueError):
    """Raised when a metadata block is syntactically invalid."""


class Metadata:
    """An immutable view over one parsed metadata block.

    Tags may appear in any order, every tag is optional, and unknown or
    duplicated keys are rejected so that typos in a map file are caught
    instead of being silently ignored.
    """

    def __init__(self, values: dict[str, str]) -> None:
        """Wrap an already validated ``key -> value`` mapping."""
        self._values = dict(values)

    @classmethod
    def empty(cls) -> "Metadata":
        """Return an empty metadata block."""
        return cls({})

    @classmethod
    def parse(cls, text: str, allowed: frozenset[str]) -> "Metadata":
        """Parse a bracketed metadata block.

        Args:
            text: The raw block, brackets included, e.g. ``[zone=normal]``.
            allowed: The set of keys accepted in this context.

        Returns:
            The parsed metadata.

        Raises:
            MetadataError: On any syntax or key violation.
        """
        stripped = text.strip()
        if not stripped.startswith("["):
            raise MetadataError("metadata block must start with '['")
        if not stripped.endswith("]"):
            raise MetadataError("metadata block must end with ']'")
        body = stripped[1:-1]
        if "[" in body or "]" in body:
            raise MetadataError("nested brackets are not allowed")
        values: dict[str, str] = {}
        for token in body.split():
            if token.count("=") != 1:
                raise MetadataError(
                    f"malformed metadata tag {token!r} (expected key=value)"
                )
            key, value = token.split("=")
            if not key or not value:
                raise MetadataError(
                    f"malformed metadata tag {token!r} (empty key or value)"
                )
            if key not in allowed:
                expected = ", ".join(sorted(allowed))
                raise MetadataError(
                    f"unknown metadata key {key!r} "
                    f"(expected one of: {expected})"
                )
            if key in values:
                raise MetadataError(f"duplicate metadata key {key!r}")
            values[key] = value
        return cls(values)

    def has(self, key: str) -> bool:
        """Return ``True`` when ``key`` is present."""
        return key in self._values

    def text(self, key: str, default: str) -> str:
        """Return the raw value of ``key`` or ``default``."""
        return self._values.get(key, default)

    def optional_text(self, key: str) -> str | None:
        """Return the raw value of ``key`` or ``None``."""
        return self._values.get(key)

    def positive_int(self, key: str, default: int) -> int:
        """Return ``key`` parsed as a strictly positive integer.

        Raises:
            MetadataError: If the value is not a positive integer.
        """
        raw = self._values.get(key)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            raise MetadataError(
                f"{key}={raw!r} is not an integer"
            ) from None
        if value <= 0:
            raise MetadataError(
                f"{key}={raw!r} must be a positive integer"
            )
        return value

    def __repr__(self) -> str:
        """Return a debug representation of the metadata."""
        return f"Metadata({self._values!r})"
