"""Tests for the generate_excel.py monthly report script."""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import generate_excel


@pytest.fixture
def sample_worksheet():
    worksheet = MagicMock()
    worksheet.title = "Ahmad Alsheekh_09_2024"
    worksheet.get_all_values.return_value = [
        ["Datum/Uhrzeit", "Station/Name", "Schicht", "Arbeitsstunden"],
        ["2024-09-01T08:00:00", "U Alexanderplatz", "Früh", "7.0"],
    ]
    return worksheet


def test_get_previous_month_january():
    month, year = generate_excel.get_previous_month(datetime(2024, 1, 15))
    assert (month, year) == (12, 2023)


def test_get_previous_month_general():
    month, year = generate_excel.get_previous_month(datetime(2024, 3, 10))
    assert (month, year) == (2, 2024)


def test_format_month_label():
    assert generate_excel.format_month_label(9, 2024) == "09_2024"


@patch("generate_excel.gspread.service_account_from_dict")
def test_authenticate_google(mock_service_account):
    mock_service_account.return_value = MagicMock()
    client = generate_excel.authenticate_google('{"type": "service_account"}')
    assert client is not None
    mock_service_account.assert_called_once()


def test_sheet_base_name_with_suffix():
    assert generate_excel.sheet_base_name("Ahmad Alsheekh_09_2024") == "Ahmad Alsheekh"


def test_sheet_base_name_without_suffix():
    assert generate_excel.sheet_base_name("SomeSheet") == "SomeSheet"


def test_find_month_sheets():
    spreadsheet = MagicMock()
    ws1 = MagicMock()
    ws1.title = "Ahmad Alsheekh_09_2024"
    ws2 = MagicMock()
    ws2.title = "U Alexanderplatz_09_2024"
    ws3 = MagicMock()
    ws3.title = "Other_08_2024"
    spreadsheet.worksheets.return_value = [ws1, ws2, ws3]
    result = generate_excel.find_month_sheets(spreadsheet, "09_2024")
    assert len(result) == 2


def test_categorize_sheets(sample_worksheet):
    ws_station = MagicMock()
    ws_station.title = "U Alexanderplatz_09_2024"
    employees, stations = generate_excel.categorize_sheets(
        [sample_worksheet, ws_station], {"U Alexanderplatz"}
    )
    assert len(employees) == 1
    assert len(stations) == 1


def test_worksheet_to_dataframe(sample_worksheet):
    df = generate_excel.worksheet_to_dataframe(sample_worksheet)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1


def test_excel_safe_sheet_name_truncates_long_name():
    name = "A" * 40
    safe = generate_excel.excel_safe_sheet_name(name)
    assert len(safe) <= 31


def test_excel_safe_sheet_name_avoids_duplicates():
    used = {"Sheet"}
    safe = generate_excel.excel_safe_sheet_name("Sheet", used)
    assert safe == "Sheet_1"


def test_excel_safe_sheet_name_special_chars():
    assert generate_excel.excel_safe_sheet_name("A/B:C[D]") == "A_B_C_D_"


@patch("generate_excel.pd.ExcelWriter")
@patch.object(pd.DataFrame, "to_excel")
def test_write_sheets_to_excel(mock_to_excel, mock_writer_class, sample_worksheet, tmp_path):
    mock_writer = MagicMock()
    mock_writer_class.return_value.__enter__.return_value = mock_writer
    output = tmp_path / "report.xlsx"
    generate_excel.write_sheets_to_excel([sample_worksheet], output)
    mock_writer_class.assert_called_once_with(output, engine="openpyxl")
    mock_to_excel.assert_called_once()


@patch("generate_excel.requests.post")
@patch("builtins.open")
def test_send_document_via_telegram(mock_open, mock_post):
    mock_post.return_value = MagicMock()
    mock_open.return_value.__enter__.return_value = MagicMock()
    generate_excel.send_document_via_telegram("token", "chat", Path("report.xlsx"), "caption")
    mock_post.assert_called_once()


def test_build_output_path():
    path = generate_excel.build_output_path("09_2024")
    assert path.name == "Monatsbericht_09_2024.xlsx"


@patch("generate_excel.send_document_via_telegram")
@patch("generate_excel.write_sheets_to_excel")
@patch("generate_excel.categorize_sheets")
@patch("generate_excel.find_month_sheets")
@patch("generate_excel.authenticate_google")
@patch("generate_excel.load_config")
@patch.dict(
    os.environ,
    {
        "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "TELEGRAM_BOT_TOKEN": "token",
        "TELEGRAM_CHAT_ID": "chat",
        "GOOGLE_SPREADSHEET_ID": "sheet_id",
    },
    clear=False,
)
def test_main_success(
    mock_load_config,
    mock_authenticate,
    mock_find_month_sheets,
    mock_categorize,
    mock_write_excel,
    mock_send_document,
    sample_worksheet,
):
    mock_load_config.return_value = {
        "google_service_account_json": '{"type": "service_account"}',
        "telegram_bot_token": "token",
        "telegram_chat_id": "chat",
        "spreadsheet_id": "sheet_id",
    }
    client = MagicMock()
    spreadsheet = MagicMock()
    client.open_by_key.return_value = spreadsheet
    mock_authenticate.return_value = client
    mock_find_month_sheets.return_value = [sample_worksheet]
    ws_station = MagicMock()
    ws_station.title = "U Alexanderplatz_09_2024"
    mock_categorize.return_value = ([sample_worksheet], [ws_station])

    generate_excel.main()

    mock_write_excel.assert_called_once()
    mock_send_document.assert_called_once()
