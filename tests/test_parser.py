"""Tests for :mod:`parser`: the strict map file reader.

Most cases build the input in memory with ``parse_lines`` since that is
faster and keeps the failing input next to the assertion. The fixtures
under ``tests/fixtures/invalid`` additionally exercise ``parse_file``,
the real file-reading path used by the CLI.
"""

from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, MAPS_DIR
from errors import ParseError
from network import Network
from parser import MapParser


def parse(*lines: str) -> Network:
    return MapParser().parse_lines(list(lines))


def fails(*lines: str) -> ParseError:
    with pytest.raises(ParseError) as info:
        parse(*lines)
    return info.value


def test_parses_a_minimal_valid_map() -> None:
    network = parse(
        "nb_drones: 3",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-goal",
    )
    assert network.nb_drones == 3
    assert network.start.name == "start"
    assert network.end.name == "goal"
    assert len(network.zones) == 2
    assert len(network.connections) == 1


def test_comments_and_blank_lines_are_ignored() -> None:
    network = parse(
        "# a full map",
        "",
        "nb_drones: 1  # fleet size",
        "   ",
        "start_hub: start 0 0 # comment after zone",
        "end_hub: goal 1 0",
        "connection: start-goal",
    )
    assert network.nb_drones == 1


def test_zone_metadata_is_parsed() -> None:
    network = parse(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 2 0",
        "hub: mid 1 0 [zone=restricted color=red max_drones=3]",
        "connection: start-mid",
        "connection: mid-goal",
    )
    mid = network.zone("mid")
    assert mid.zone_type.value == "restricted"
    assert mid.color == "red"
    assert mid.declared_capacity == 3


def test_max_drones_on_start_or_end_hub_is_ignored_not_an_error() -> None:
    network = parse(
        "nb_drones: 1",
        "start_hub: start 0 0 [max_drones=9]",
        "end_hub: goal 1 0 [max_drones=9]",
        "connection: start-goal",
    )
    assert network.start.capacity is None
    assert network.end.capacity is None


def test_connection_metadata_max_link_capacity() -> None:
    network = parse(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-goal [max_link_capacity=4]",
    )
    assert network.connection("start", "goal").capacity == 4


def test_first_meaningful_line_must_be_nb_drones() -> None:
    error = fails("start_hub: start 0 0", "end_hub: goal 1 0")
    assert "nb_drones" in error.reason
    assert error.line_number == 1


def test_nb_drones_declared_twice_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "nb_drones: 2",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
    )
    assert "more than once" in error.reason


@pytest.mark.parametrize("value", ["0", "-1", "abc", ""])
def test_nb_drones_must_be_a_positive_integer(value: str) -> None:
    fails(f"nb_drones: {value}", "start_hub: s 0 0", "end_hub: e 1 0")


def test_missing_start_hub_is_rejected() -> None:
    error = fails("nb_drones: 1", "end_hub: goal 0 0")
    assert "start hub" in str(error)


def test_missing_end_hub_is_rejected() -> None:
    error = fails("nb_drones: 1", "start_hub: start 0 0")
    assert "end hub" in str(error)


def test_start_and_end_must_be_distinct_zones() -> None:
    with pytest.raises(ParseError):
        parse(
            "nb_drones: 1",
            "start_hub: same 0 0",
            "hub: same 1 1",
        )


def test_duplicate_zone_name_is_rejected() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "hub: start 2 2",
    )


def test_dash_in_zone_name_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "hub: bad-name 0 1",
    )
    assert "forbidden character" in error.reason


def test_space_in_zone_body_wrong_field_count() -> None:
    fails("nb_drones: 1", "start_hub: start 0", "end_hub: goal 1 0")


def test_non_integer_coordinate_is_rejected() -> None:
    fails("nb_drones: 1", "start_hub: start a 0", "end_hub: goal 1 0")


def test_unknown_zone_type_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "hub: mid 0 1 [zone=hazardous]",
    )
    assert "unknown zone type" in error.reason


def test_connection_must_use_a_dash_with_no_surrounding_spaces() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start - goal",
    )


def test_connection_needs_exactly_two_named_endpoints() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-",
    )


def test_connection_to_undefined_zone_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-nowhere",
    )
    assert "undefined zone" in error.reason


def test_connection_self_loop_is_rejected() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-start",
    )


def test_duplicate_connection_either_orientation_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "connection: start-goal",
        "connection: goal-start",
    )
    assert "already defined" in error.reason


def test_unknown_metadata_key_is_rejected() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "hub: mid 0 1 [speed=fast]",
    )


def test_non_positive_capacity_is_rejected() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "hub: mid 0 1 [max_drones=0]",
    )


def test_unrecognised_line_prefix_is_rejected() -> None:
    error = fails(
        "nb_drones: 1",
        "start_hub: start 0 0",
        "end_hub: goal 1 0",
        "teleport: start-goal",
    )
    assert "unrecognised line" in error.reason


def test_closing_bracket_without_opening_is_rejected() -> None:
    fails(
        "nb_drones: 1",
        "start_hub: start 0 0]",
        "end_hub: goal 1 0",
    )


FIXTURE_FILES: list[Path] = sorted(FIXTURES_DIR.glob("*.map"))


@pytest.mark.parametrize(
    "path", FIXTURE_FILES, ids=[path.stem for path in FIXTURE_FILES]
)
def test_every_invalid_fixture_map_is_rejected(path: Path) -> None:
    with pytest.raises(ParseError):
        MapParser().parse_file(str(path))


def test_fixture_directory_is_not_empty() -> None:
    assert len(FIXTURE_FILES) >= 10


REAL_MAPS: list[Path] = sorted(MAPS_DIR.glob("*/*.txt"))


@pytest.mark.parametrize(
    "path", REAL_MAPS, ids=[path.stem for path in REAL_MAPS]
)
def test_every_shipped_subject_map_parses_cleanly(path: Path) -> None:
    network = MapParser().parse_file(str(path))
    assert network.nb_drones > 0
    assert network.start.name != network.end.name
