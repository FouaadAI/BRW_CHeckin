"""Unit tests for Google Sheets helpers with mocked gspread."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.sheets_helpers import (
    build_employee_sheet_name,
    build_station_sheet_name,
    ensure_sheet_exists,
    format_checkin_row,
    format_employee_row,
    format_station_row,
    google_maps_link,
    month_year_suffix,
    normalize_sheet_title,
    recent_checkin_exists,
    shift_hours,
)


@pytest.fixture
def fixed_time():
    return datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)


def test_normalize_sheet_title_removes_invalid_chars():
    assert normalize_sheet_title("U Alexanderplatz_09_2024") == "U Alexanderplatz_09_2024"
    assert normalize_sheet_title("U <Test>") == "U _Test_"
    assert normalize_sheet_title('U :"/\\|?*') == "U _______"


def test_normalize_sheet_title_truncates_to_100_chars():
    long_name = "A" * 120
    assert len(normalize_sheet_title(long_name)) == 100


def test_normalize_sheet_title_defaults_to_sheet():
    assert normalize_sheet_title("") == "Sheet"
    assert normalize_sheet_title(' <> ') == "Sheet"


def test_month_year_suffix(fixed_time):
    assert month_year_suffix(fixed_time) == "09_2024"


def test_build_employee_sheet_name(fixed_time):
    assert build_employee_sheet_name("Max Mustermann", fixed_time) == "Max Mustermann_09_2024"


def test_build_station_sheet_name(fixed_time):
    assert build_station_sheet_name("U Alexanderplatz", fixed_time) == "U Alexanderplatz_09_2024"


def test_shift_hours_known_shifts():
    assert shift_hours("Früh") == 7.0
    assert shift_hours("Spät") == 7.0
    assert shift_hours("Nacht") == 7.0


def test_shift_hours_defaults_to_seven():
    assert shift_hours("Mittag") == 7.0


def test_google_maps_link():
    assert google_maps_link(52.5, 13.4) == "https://www.google.com/maps?q=52.5,13.4"


def test_format_checkin_row(fixed_time):
    row = format_checkin_row(fixed_time, "U Alexanderplatz", "Früh", 42.5, 52.52, 13.41)
    assert row[0] == fixed_time.isoformat()
    assert row[1] == "U Alexanderplatz"
    assert row[2] == "Früh"
    assert row[3] == 7.0
    assert row[4] == 42.5
    assert row[5] == 52.52
    assert row[6] == 13.41
    assert row[7] == "https://www.google.com/maps?q=52.52,13.41"


def test_format_employee_row_matches_checkin_row(fixed_time):
    row = format_employee_row(fixed_time, "U Alexanderplatz", "Früh", 42.5, 52.52, 13.41)
    assert len(row) == 8
    assert row[3] == 7.0


def test_format_station_row_includes_name(fixed_time):
    row = format_station_row(fixed_time, "Max Mustermann", "Spät", 10.0, 52.0, 13.0)
    assert row[1] == "Max Mustermann"


def test_ensure_sheet_exists_returns_existing_worksheet():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet

    result = ensure_sheet_exists(spreadsheet, "Max Mustermann_09_2024")

    spreadsheet.worksheet.assert_called_once_with("Max Mustermann_09_2024")
    spreadsheet.add_worksheet.assert_not_called()
    assert result is worksheet


def test_ensure_sheet_exists_creates_missing_worksheet():
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = Exception("not found")
    new_worksheet = MagicMock()
    spreadsheet.add_worksheet.return_value = new_worksheet

    result = ensure_sheet_exists(spreadsheet, "U Alexanderplatz_09_2024")

    spreadsheet.add_worksheet.assert_called_once_with(title="U Alexanderplatz_09_2024", rows=1000, cols=10)
    new_worksheet.append_row.assert_called_once()
    assert result is new_worksheet


def test_recent_checkin_exists_false_when_worksheet_missing():
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = Exception("not found")
    timestamp = datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert recent_checkin_exists(spreadsheet, "Max Mustermann", timestamp) is False


def test_recent_checkin_exists_false_when_no_rows():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [["Datum/Uhrzeit"]]
    spreadsheet.worksheet.return_value = worksheet
    timestamp = datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert recent_checkin_exists(spreadsheet, "Max Mustermann", timestamp) is False


def test_recent_checkin_exists_true_within_threshold():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    row_ts = datetime(2024, 9, 15, 12, 28, 0, tzinfo=timezone.utc).isoformat()
    worksheet.get_all_values.return_value = [["Datum/Uhrzeit"], [row_ts, "Station"]]
    spreadsheet.worksheet.return_value = worksheet
    timestamp = datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert recent_checkin_exists(spreadsheet, "Max Mustermann", timestamp, minutes=5) is True


def test_recent_checkin_exists_false_outside_threshold():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    row_ts = datetime(2024, 9, 15, 11, 0, 0, tzinfo=timezone.utc).isoformat()
    worksheet.get_all_values.return_value = [["Datum/Uhrzeit"], [row_ts, "Station"]]
    spreadsheet.worksheet.return_value = worksheet
    timestamp = datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert recent_checkin_exists(spreadsheet, "Max Mustermann", timestamp, minutes=5) is False


def test_recent_checkin_exists_ignores_unparseable_timestamps():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [["Datum/Uhrzeit"], ["invalid", "Station"]]
    spreadsheet.worksheet.return_value = worksheet
    timestamp = datetime(2024, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert recent_checkin_exists(spreadsheet, "Max Mustermann", timestamp) is False
