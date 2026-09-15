"""Payload validation for repository dispatch events."""

import json
from typing import Any

REQUIRED_FIELDS = {"pin", "name", "station", "shift", "latitude", "longitude", "distance_m", "timestamp"}
VALID_SHIFTS = {"Früh", "Spät", "Nacht"}


def load_employees(path: str = "employees.json") -> set[str]:
    """Load the whitelist of allowed employee names."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data)


def load_stations(path: str = "stations.json") -> set[str]:
    """Load the whitelist of allowed station names."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {station["name"] for station in data}


def validate_pin(pin: Any, expected_pin: str) -> tuple[bool, str]:
    """Validate PIN length and value."""
    if not isinstance(pin, str):
        return False, "PIN muss ein String sein."
    if len(pin) != len(expected_pin):
        return False, f"PIN muss {len(expected_pin)} Zeichen lang sein."
    if pin != expected_pin:
        return False, "Ungültige PIN."
    return True, ""


def validate_required_fields(payload: dict) -> tuple[bool, str]:
    """Ensure all required check-in fields are present and non-empty."""
    missing = REQUIRED_FIELDS - set(payload.keys())
    if missing:
        return False, f"Fehlende Felder: {', '.join(sorted(missing))}"

    empty = [key for key in REQUIRED_FIELDS if payload.get(key) in (None, "", [])]
    if empty:
        return False, f"Leere Pflichtfelder: {', '.join(sorted(empty))}"

    return True, ""


def validate_shift(shift: Any) -> tuple[bool, str]:
    """Validate shift value."""
    if shift not in VALID_SHIFTS:
        return False, f"Ungültige Schicht. Erlaubt: {', '.join(sorted(VALID_SHIFTS))}"
    return True, ""


def validate_coordinates(lat: Any, lng: Any) -> tuple[bool, str]:
    """Validate GPS coordinates are numeric and in valid ranges."""
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return False, "GPS-Koordinaten müssen numerisch sein."

    if not (-90 <= lat_f <= 90):
        return False, "Breitengrad muss zwischen -90 und 90 liegen."
    if not (-180 <= lng_f <= 180):
        return False, "Längengrad muss zwischen -180 und 180 liegen."

    return True, ""


def validate_distance(distance_m: Any, max_m: float = 200.0) -> tuple[bool, str]:
    """Validate distance is numeric and within geofence radius."""
    try:
        distance_f = float(distance_m)
    except (TypeError, ValueError):
        return False, "Distanz muss numerisch sein."

    if distance_f < 0:
        return False, "Distanz darf nicht negativ sein."
    if distance_f > max_m:
        return False, f"Distanz überschreitet {max_m} m (gemessen: {distance_f} m)."

    return True, ""


def validate_whitelist(
    name: Any, station: Any, employees: set[str], stations: set[str]
) -> tuple[bool, str]:
    """Validate employee and station exist in their whitelists."""
    if name not in employees:
        return False, "Mitarbeiter nicht in der Whitelist."
    if station not in stations:
        return False, "Station nicht in der Whitelist."
    return True, ""


def validate_payload(
    payload: dict,
    expected_pin: str,
    employees: set[str],
    stations: set[str],
    max_distance_m: float = 200.0,
) -> tuple[bool, str]:
    """Run all payload validation checks."""
    checks = [
        validate_required_fields(payload),
        validate_pin(payload.get("pin"), expected_pin),
        validate_shift(payload.get("shift")),
        validate_coordinates(payload.get("latitude"), payload.get("longitude")),
        validate_distance(payload.get("distance_m"), max_m=max_distance_m),
        validate_whitelist(
            payload.get("name"), payload.get("station"), employees, stations
        ),
    ]

    for ok, message in checks:
        if not ok:
            return False, message

    return True, ""
