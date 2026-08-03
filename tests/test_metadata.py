"""Tests for the ``[key=value ...]`` metadata block parser."""

import pytest

from metadata import Metadata, MetadataError

ZONE_KEYS = frozenset({"zone", "color", "max_drones"})


def test_empty_metadata_has_no_keys() -> None:
    metadata = Metadata.empty()
    assert metadata.has("zone") is False
    assert metadata.text("zone", "normal") == "normal"
    assert metadata.optional_text("color") is None


def test_parse_single_tag() -> None:
    metadata = Metadata.parse("[zone=restricted]", ZONE_KEYS)
    assert metadata.has("zone") is True
    assert metadata.text("zone", "normal") == "restricted"


def test_parse_multiple_tags_in_any_order() -> None:
    metadata = Metadata.parse(
        "[max_drones=3 color=blue zone=priority]", ZONE_KEYS
    )
    assert metadata.text("zone", "normal") == "priority"
    assert metadata.optional_text("color") == "blue"
    assert metadata.positive_int("max_drones", 1) == 3


@pytest.mark.parametrize(
    "block",
    [
        "zone=normal]",
        "[zone=normal",
        "[zone==normal]",
        "[zone]",
        "[=normal]",
        "[zone=normal color=[blue]]",
        "[zone=normal zone=priority]",
        "[unknown=1]",
    ],
)
def test_rejects_malformed_or_illegal_blocks(block: str) -> None:
    with pytest.raises(MetadataError):
        Metadata.parse(block, ZONE_KEYS)


def test_positive_int_returns_default_when_absent() -> None:
    metadata = Metadata.empty()
    assert metadata.positive_int("max_drones", 1) == 1


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "1.5"])
def test_positive_int_rejects_invalid_values(raw: str) -> None:
    metadata = Metadata.parse(f"[max_drones={raw}]", ZONE_KEYS)
    with pytest.raises(MetadataError):
        metadata.positive_int("max_drones", 1)
