"""Google Sheets formatting and normalization helpers."""

import re
from datetime import datetime, timedelta, timezone


SHIFT_HOURS = {"Früh": 7.0, "Spät": 7.0, "Nacht": 7.0}


def normalize_sheet_title(raw: str) -> str:
    """Create a gspread-safe sheet title."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", str(raw))
    cleaned = cleaned.strip()[:100]
    if not cleaned or not cleaned.replace("_", "").strip():
        return "Sheet"
    return cleaned


def month_year_suffix(timestamp: datetime | None = None) -> str:
    """Return MM_YYYY suffix used for monthly sheets."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    return f"{timestamp.month:02d}_{timestamp.year}"


def build_employee_sheet_name(name: str, timestamp: datetime | None = None) -> str:
    """Return '{Name}_{MM_YYYY}' formatted for a Google Sheets tab."""
    return normalize_sheet_title(f"{name}_{month_year_suffix(timestamp)}")


def build_station_sheet_name(station: str, timestamp: datetime | None = None) -> str:
    """Return '{Station}_{MM_YYYY}' formatted for a Google Sheets tab."""
    return normalize_sheet_title(f"{station}_{month_year_suffix(timestamp)}")


def shift_hours(shift: str) -> float:
    """Return default working hours for a shift (7.0)."""
    return SHIFT_HOURS.get(shift, 7.0)


def google_maps_link(lat: float, lng: float) -> str:
    """Return a Google Maps link for a GPS coordinate."""
    return f"https://www.google.com/maps?q={lat},{lng}"


def format_checkin_row(
    timestamp: datetime,
    station: str,
    shift: str,
    distance_m: float,
    lat: float,
    lng: float,
) -> list:
    """Format a common row for both employee and station sheets."""
    return [
        timestamp.isoformat(),
        station,
        shift,
        shift_hours(shift),
        round(distance_m, 2),
        lat,
        lng,
        google_maps_link(lat, lng),
    ]


def format_employee_row(
    timestamp: datetime,
    station: str,
    shift: str,
    distance_m: float,
    lat: float,
    lng: float,
) -> list:
    """Format a row for the employee sheet."""
    return format_checkin_row(timestamp, station, shift, distance_m, lat, lng)


def format_station_row(
    timestamp: datetime,
    name: str,
    shift: str,
    distance_m: float,
    lat: float,
    lng: float,
) -> list:
    """Format a row for the station sheet with the employee name."""
    return [
        timestamp.isoformat(),
        name,
        shift,
        shift_hours(shift),
        round(distance_m, 2),
        lat,
        lng,
        google_maps_link(lat, lng),
    ]


def ensure_sheet_exists(spreadsheet, title: str):
    """Return an existing worksheet or create it with expected headers."""
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=10)
        worksheet.append_row(
            [
                "Datum/Uhrzeit",
                "Station/Name",
                "Schicht",
                "Arbeitsstunden",
                "Abweichung (m)",
                "GPS Lat",
                "GPS Long",
                "Google Maps Link",
            ]
        )
    return worksheet


def recent_checkin_exists(
    spreadsheet,
    name: str,
    timestamp: datetime,
    minutes: int = 5,
) -> bool:
    """Return True if the employee already has a check-in within `minutes`."""
    title = build_employee_sheet_name(name, timestamp)
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception:
        return False

    rows = worksheet.get_all_values()
    if len(rows) <= 1:
        return False

    threshold = timedelta(minutes=minutes)
    for row in rows[1:]:
        if not row:
            continue
        try:
            row_ts = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if abs((timestamp - row_ts).total_seconds()) <= threshold.total_seconds():
            return True
    return False
