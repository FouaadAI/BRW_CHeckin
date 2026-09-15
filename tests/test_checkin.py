"""Tests for the checkin.py workflow script."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import checkin


@pytest.fixture
def valid_payload():
    return {
        "pin": "123456",
        "name": "Ahmad Alsheekh",
        "station": "U Alexanderplatz",
        "shift": "Früh",
        "latitude": 52.521585,
        "longitude": 13.413908,
        "distance_m": 42,
        "timestamp": "2024-09-15T08:00:00+02:00",
    }


@pytest.fixture
def event_path(tmp_path: Path, valid_payload):
    path = tmp_path / "event.json"
    path.write_text(json.dumps({"client_payload": valid_payload}), encoding="utf-8")
    return str(path)


def test_load_payload_reads_github_event(event_path, valid_payload):
    with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_path}, clear=False):
        assert checkin.load_payload() == valid_payload


def test_load_payload_missing_event_path():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvironmentError):
            checkin.load_payload()


def test_load_payload_missing_client_payload(event_path):
    event_path_path = Path(event_path)
    event_path_path.write_text(json.dumps({}), encoding="utf-8")
    with patch.dict(os.environ, {"GITHUB_EVENT_PATH": event_path}, clear=False):
        with pytest.raises(ValueError):
            checkin.load_payload()


def test_get_required_env_present():
    with patch.dict(os.environ, {"TEST_VAR": "value"}, clear=False):
        assert checkin.get_required_env("TEST_VAR") == "value"


def test_get_required_env_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(EnvironmentError):
            checkin.get_required_env("MISSING")


def test_validate_pin_ok():
    checkin.validate_pin("123456", "123456")


def test_validate_pin_mismatch():
    with pytest.raises(PermissionError):
        checkin.validate_pin("000000", "123456")


def test_validate_payload_ok(valid_payload):
    result = checkin.validate_payload(valid_payload)
    assert result["name"] == valid_payload["name"]


def test_validate_payload_missing_field(valid_payload):
    payload = {k: v for k, v in valid_payload.items() if k != "name"}
    with pytest.raises(ValueError):
        checkin.validate_payload(payload)


def test_validate_payload_wrong_type(valid_payload):
    payload = {**valid_payload, "latitude": "not-a-number"}
    with pytest.raises(ValueError):
        checkin.validate_payload(payload)


def test_validate_payload_invalid_shift(valid_payload):
    payload = {**valid_payload, "shift": "Morgen"}
    with pytest.raises(ValueError):
        checkin.validate_payload(payload)


def test_normalize_sheet_name_removes_invalid_chars():
    assert checkin.normalize_sheet_name('Ahmad:name/?*\\') == "Ahmadname"


def test_normalize_sheet_name_truncates_long_name():
    long_name = "A" * 120
    assert len(checkin.normalize_sheet_name(long_name)) == 100


def test_normalize_sheet_name_empty_becomes_unbenannt():
    assert checkin.normalize_sheet_name(':/\\?*') == "Unbenannt"


def test_month_suffix_from_timestamp():
    assert checkin.month_suffix_from_timestamp("2024-09-15T08:00:00+02:00") == "09_2024"


def test_month_suffix_from_timestamp_invalid():
    with pytest.raises(ValueError):
        checkin.month_suffix_from_timestamp("not-a-timestamp")


def test_build_google_maps_link():
    link = checkin.build_google_maps_link(52.0, 13.0)
    assert link == "https://www.google.com/maps?q=52.0,13.0"


def test_build_row():
    row = checkin.build_row("2024-09-15T08:00:00", "Station", "Früh", 42.5, 52.0, 13.0)
    assert len(row) == 8
    assert row[3] == "7.0"


def test_get_or_create_worksheet_existing():
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet
    assert checkin.get_or_create_worksheet(spreadsheet, "Sheet") == worksheet
    spreadsheet.worksheet.assert_called_once_with("Sheet")
    spreadsheet.add_worksheet.assert_not_called()


def test_get_or_create_worksheet_creates_new():
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = checkin.gspread.WorksheetNotFound("missing")
    new_ws = MagicMock()
    spreadsheet.add_worksheet.return_value = new_ws
    result = checkin.get_or_create_worksheet(spreadsheet, "Sheet")
    assert result == new_ws
    assert new_ws.append_row.call_count == 2


def test_append_checkin_row():
    worksheet = MagicMock()
    checkin.append_checkin_row(worksheet, ["row"])
    worksheet.append_row.assert_called_once()


def test_update_monthly_hours():
    worksheet = MagicMock()
    checkin.update_monthly_hours(worksheet)
    worksheet.update_cell.assert_called_once_with(2, 4, "=SUM(D3:D)")


@patch("checkin.requests.post")
def test_send_telegram_message(mock_post):
    mock_post.return_value = MagicMock()
    checkin.send_telegram_message("token", "chat", "Name", "Station", "Früh", 42, "http://map")
    mock_post.assert_called_once()


@patch("checkin.send_telegram_message")
@patch("checkin.open_spreadsheet")
@patch("checkin.get_or_create_worksheet")
@patch("checkin.recent_checkin_exists")
@patch("checkin.append_checkin_row")
@patch("checkin.update_monthly_hours")
@patch("checkin.load_payload")
@patch.dict(
    os.environ,
    {
        "APP_PIN": "123456",
        "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "TELEGRAM_BOT_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat",
        "GOOGLE_SPREADSHEET_ID": "sheet_id",
    },
    clear=False,
)
def test_process_checkin_success(
    mock_load_payload,
    mock_update_hours,
    mock_append_row,
    mock_recent_checkin,
    mock_get_or_create,
    mock_open_spreadsheet,
    mock_send_telegram,
    valid_payload,
):
    mock_load_payload.return_value = valid_payload
    mock_recent_checkin.return_value = False
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    mock_open_spreadsheet.return_value = spreadsheet
    mock_get_or_create.return_value = worksheet
    checkin.process_checkin()
    assert mock_append_row.call_count == 2
    mock_update_hours.assert_called_once()
    mock_send_telegram.assert_called_once()


@patch("checkin.recent_checkin_exists")
@patch("checkin.load_payload")
@patch.dict(
    os.environ,
    {
        "APP_PIN": "123456",
        "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "TELEGRAM_BOT_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat",
        "GOOGLE_SPREADSHEET_ID": "sheet_id",
    },
    clear=False,
)
def test_process_checkin_rejected_by_cooldown(
    mock_load_payload,
    mock_recent_checkin,
    valid_payload,
):
    mock_load_payload.return_value = valid_payload
    mock_recent_checkin.return_value = True
    with pytest.raises(ValueError):
        checkin.process_checkin()
