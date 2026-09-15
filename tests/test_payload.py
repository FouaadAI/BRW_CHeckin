"""Unit tests for payload validation helpers."""

import pytest

from src.payload_validator import (
    validate_coordinates,
    validate_distance,
    validate_payload,
    validate_pin,
    validate_required_fields,
    validate_shift,
    validate_whitelist,
)


@pytest.fixture
def valid_payload():
    return {
        "pin": "1234",
        "name": "Max Mustermann",
        "station": "U Alexanderplatz",
        "shift": "Früh",
        "latitude": 52.521585,
        "longitude": 13.413908,
        "distance_m": 42.0,
        "timestamp": "2024-09-15T12:30:00+00:00",
    }


def test_validate_required_fields_all_present(valid_payload):
    ok, msg = validate_required_fields(valid_payload)
    assert ok is True
    assert msg == ""


def test_validate_required_fields_missing():
    ok, msg = validate_required_fields({"pin": "1234", "name": "Max"})
    assert ok is False
    assert "Fehlende Felder" in msg


def test_validate_required_fields_empty_values(valid_payload):
    payload = {**valid_payload, "station": ""}
    ok, msg = validate_required_fields(payload)
    assert ok is False
    assert "Leere Pflichtfelder" in msg


def test_validate_pin_correct():
    ok, msg = validate_pin("1234", "1234")
    assert ok is True
    assert msg == ""


def test_validate_pin_wrong():
    ok, msg = validate_pin("0000", "1234")
    assert ok is False
    assert "Ungültige PIN" in msg


def test_validate_pin_wrong_length():
    ok, msg = validate_pin("123", "1234")
    assert ok is False
    assert "4 Zeichen" in msg


def test_validate_pin_non_string():
    ok, msg = validate_pin(1234, "1234")
    assert ok is False
    assert "String" in msg


def test_validate_shift_valid():
    ok, msg = validate_shift("Nacht")
    assert ok is True
    assert msg == ""


def test_validate_shift_invalid():
    ok, msg = validate_shift("Mittag")
    assert ok is False
    assert "Ungültige Schicht" in msg


def test_validate_coordinates_valid():
    ok, msg = validate_coordinates(52.52, 13.41)
    assert ok is True
    assert msg == ""


def test_validate_coordinates_out_of_range():
    ok, msg = validate_coordinates(95.0, 13.41)
    assert ok is False
    assert "Breitengrad" in msg

    ok, msg = validate_coordinates(52.52, 190.0)
    assert ok is False
    assert "Längengrad" in msg


def test_validate_coordinates_non_numeric():
    ok, msg = validate_coordinates("abc", 13.41)
    assert ok is False
    assert "numerisch" in msg


def test_validate_distance_within_radius():
    ok, msg = validate_distance(150.0)
    assert ok is True
    assert msg == ""


def test_validate_distance_exceeds_radius():
    ok, msg = validate_distance(250.0)
    assert ok is False
    assert "überschreitet 200.0 m" in msg


def test_validate_distance_negative():
    ok, msg = validate_distance(-1.0)
    assert ok is False
    assert "negativ" in msg


def test_validate_distance_non_numeric():
    ok, msg = validate_distance("weit")
    assert ok is False
    assert "numerisch" in msg


def test_validate_whitelist_valid():
    ok, msg = validate_whitelist("Max", "U Alexanderplatz", {"Max"}, {"U Alexanderplatz"})
    assert ok is True
    assert msg == ""


def test_validate_whitelist_invalid_employee():
    ok, msg = validate_whitelist("Eve", "U Alexanderplatz", {"Max"}, {"U Alexanderplatz"})
    assert ok is False
    assert "Mitarbeiter" in msg


def test_validate_whitelist_invalid_station():
    ok, msg = validate_whitelist("Max", "U Fake", {"Max"}, {"U Alexanderplatz"})
    assert ok is False
    assert "Station" in msg


def test_validate_payload_full(valid_payload):
    ok, msg = validate_payload(
        valid_payload,
        expected_pin="1234",
        employees={"Max Mustermann"},
        stations={"U Alexanderplatz"},
    )
    assert ok is True
    assert msg == ""


def test_validate_payload_bad_pin(valid_payload):
    payload = {**valid_payload, "pin": "0000"}
    ok, msg = validate_payload(
        payload,
        expected_pin="1234",
        employees={"Max Mustermann"},
        stations={"U Alexanderplatz"},
    )
    assert ok is False
    assert "PIN" in msg


def test_validate_payload_too_far(valid_payload):
    payload = {**valid_payload, "distance_m": 250.0}
    ok, msg = validate_payload(
        payload,
        expected_pin="1234",
        employees={"Max Mustermann"},
        stations={"U Alexanderplatz"},
    )
    assert ok is False
    assert "überschreitet" in msg


def test_validate_payload_whitelist_fail(valid_payload):
    ok, msg = validate_payload(
        valid_payload,
        expected_pin="1234",
        employees={"Erika Musterfrau"},
        stations={"U Alexanderplatz"},
    )
    assert ok is False
    assert "Mitarbeiter" in msg
