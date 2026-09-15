"""BRW Check-in backend for serverless time tracking.

Reads a repository-dispatch payload, validates PIN and fields, appends rows to
Google Sheets and sends a Telegram notification.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

import gspread
import requests
from gspread.utils import ValueInputOption

from src.sheets_helpers import recent_checkin_exists

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("checkin")

SHIFT_HOURS = 7.0
VALID_SHIFTS = {"Früh", "Spät", "Nacht"}
SHEET_NAME_MAX_LEN = 100
INVALID_SHEET_CHARS = ':*?/\\\''


def load_payload() -> dict[str, Any]:
    """Load the repository_dispatch client_payload from GITHUB_EVENT_PATH."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise EnvironmentError("GITHUB_EVENT_PATH is not set")

    with open(event_path, "r", encoding="utf-8") as file:
        event = json.load(file)

    payload = event.get("client_payload")
    if not isinstance(payload, dict):
        raise ValueError("client_payload is missing or not an object")

    return payload


def get_required_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set")
    return value


def validate_dispatch_secret(provided_secret: Any, expected_secret: str) -> None:
    """Abort execution if the repository_dispatch secret does not match."""
    if not isinstance(provided_secret, str) or provided_secret != expected_secret:
        raise PermissionError("Dispatch secret mismatch: check-in denied")


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure all required payload fields are present and of the right type."""
    required_fields = {
        "pin": str,
        "name": str,
        "station": str,
        "shift": str,
        "latitude": (int, float),
        "longitude": (int, float),
        "distance_m": (int, float),
        "timestamp": str,
    }

    errors = []
    for field, expected_type in required_fields.items():
        if field not in payload:
            errors.append(f"Missing field: {field}")
            continue
        value = payload[field]
        if not isinstance(value, expected_type):
            errors.append(f"Field '{field}' must be {expected_type.__name__ if isinstance(expected_type, type) else 'numeric'}")

    if errors:
        raise ValueError("Payload validation failed: " + "; ".join(errors))

    validated = {field: payload[field] for field in required_fields}

    validated = {field: payload[field] for field in required_fields}

    if validated["shift"] not in VALID_SHIFTS:
        raise ValueError("Payload validation failed: shift must be Früh, Spät or Nacht")

    return validated


def normalize_sheet_name(raw_name: str) -> str:
    """Create a valid Google Sheets worksheet name (max 100 chars)."""
    cleaned = "".join(char for char in raw_name if char not in INVALID_SHEET_CHARS)
    cleaned = cleaned.strip()
    if not cleaned:
        cleaned = "Unbenannt"
    return cleaned[:SHEET_NAME_MAX_LEN]


def month_suffix_from_timestamp(timestamp: str) -> str:
    """Return MM_YYYY extracted from an ISO-like timestamp."""
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid timestamp: {timestamp!r}") from exc
    return parsed.strftime("%m_%Y")


def build_google_maps_link(latitude: float, longitude: float) -> str:
    """Return a Google Maps URL for the given coordinates."""
    return f"https://www.google.com/maps?q={latitude},{longitude}"


def build_row(
    timestamp: str,
    station_or_name: str,
    shift: str,
    distance_m: float,
    latitude: float,
    longitude: float,
) -> list[str]:
    """Format a single row for appending to a worksheet."""
    return [
        timestamp,
        station_or_name,
        shift,
        str(SHIFT_HOURS),
        str(distance_m),
        str(latitude),
        str(longitude),
        build_google_maps_link(latitude, longitude),
    ]


def get_or_create_worksheet(spreadsheet: gspread.Spreadsheet, title: str) -> gspread.Worksheet:
    """Fetch an existing worksheet or create it with default headers."""
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=100, cols=10)
        worksheet.append_row(
            [
                "Datum/Uhrzeit",
                "Station / Name",
                "Schicht",
                "Arbeitsstunden",
                "Abweichung (m)",
                "GPS Lat",
                "GPS Long",
                "Google Maps Link",
            ]
        )
        worksheet.append_row(["Gesamtstunden", "", "", "=SUM(D3:D)", "", "", "", ""])
        return worksheet


def append_checkin_row(worksheet: gspread.Worksheet, row: list[str]) -> None:
    """Append a single row to the given worksheet."""
    worksheet.append_row(row, value_input_option=ValueInputOption.user_entered)


def update_monthly_hours(worksheet: gspread.Worksheet) -> None:
    """Refresh the monthly total formula in the employee worksheet."""
    worksheet.update_cell(2, 4, "=SUM(D3:D)")


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    name: str,
    station: str,
    shift: str,
    distance_m: float,
    maps_link: str,
) -> None:
    """Send a German notification via the Telegram Bot API."""
    text = (
        f"✅ Check-in bestätigt\n"
        f"Name: {name}\n"
        f"Station: {station}\n"
        f"Schicht: {shift}\n"
        f"Distanz: {distance_m} m\n"
        f"Karte: {maps_link}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
        timeout=30,
    )
    response.raise_for_status()


def open_spreadsheet(credentials_json: str, spreadsheet_id: str) -> gspread.Spreadsheet:
    """Authenticate with Google and open the target spreadsheet."""
    credentials = json.loads(credentials_json)
    client = gspread.service_account_from_dict(credentials)
    return client.open_by_key(spreadsheet_id)


def process_checkin() -> None:
    """Main entry point for the repository dispatch check-in workflow."""
    dispatch_secret = get_required_env("DISPATCH_SECRET")
    credentials_json = get_required_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    telegram_token = get_required_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = get_required_env("TELEGRAM_CHAT_ID")
    spreadsheet_id = get_required_env("GOOGLE_SPREADSHEET_ID")

    payload = load_payload()
    validate_dispatch_secret(payload.get("dispatch_secret"), dispatch_secret)
    validated = validate_payload(payload)

    timestamp = validated["timestamp"]
    month_suffix = month_suffix_from_timestamp(timestamp)

    employee_sheet_name = normalize_sheet_name(f"{validated['name']}_{month_suffix}")
    station_sheet_name = normalize_sheet_name(f"{validated['station']}_{month_suffix}")

    spreadsheet = open_spreadsheet(credentials_json, spreadsheet_id)

    timestamp_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if recent_checkin_exists(spreadsheet, validated["name"], timestamp_dt, minutes=5):
        raise ValueError("Check-in too soon for this employee (5-minute cooldown)")

    employee_worksheet = get_or_create_worksheet(spreadsheet, employee_sheet_name)
    employee_row = build_row(
        timestamp,
        validated["station"],
        validated["shift"],
        float(validated["distance_m"]),
        float(validated["latitude"]),
        float(validated["longitude"]),
    )
    append_checkin_row(employee_worksheet, employee_row)
    update_monthly_hours(employee_worksheet)

    station_worksheet = get_or_create_worksheet(spreadsheet, station_sheet_name)
    station_row = build_row(
        timestamp,
        validated["name"],
        validated["shift"],
        float(validated["distance_m"]),
        float(validated["latitude"]),
        float(validated["longitude"]),
    )
    append_checkin_row(station_worksheet, station_row)

    maps_link = build_google_maps_link(
        float(validated["latitude"]), float(validated["longitude"])
    )
    send_telegram_message(
        telegram_token,
        telegram_chat_id,
        validated["name"],
        validated["station"],
        validated["shift"],
        float(validated["distance_m"]),
        maps_link,
    )

    logger.info("Check-in processed for %s at %s", validated["name"], validated["station"])


if __name__ == "__main__":
    try:
        process_checkin()
    except Exception as error:
        logger.error("Check-in failed: %s", error)
        sys.exit(1)
