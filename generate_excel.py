"""Generate and deliver the monthly BRW Check-in Excel report.

Reads the previous month's worksheets from Google Sheets, combines them into a
single Excel workbook and sends the file via Telegram.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import gspread
import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SUFFIX_PATTERN = re.compile(r"_(\d{2})_(\d{4})$")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def require_env(name: str) -> str:
    """Return an environment variable or raise a clear error."""
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Environment variable {name} is not set")
    return value


def load_config() -> dict:
    """Load all required configuration from environment variables."""
    return {
        "google_service_account_json": require_env("GOOGLE_SERVICE_ACCOUNT_JSON"),
        "telegram_bot_token": require_env("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": require_env("TELEGRAM_CHAT_ID"),
        "spreadsheet_id": require_env("GOOGLE_SPREADSHEET_ID"),
    }


def get_previous_month(reference_date: datetime | None = None) -> tuple[int, int]:
    """Return (month, year) for the month before the reference date."""
    ref = reference_date or datetime.now()
    first_of_current = datetime(ref.year, ref.month, 1)
    last_of_previous = first_of_current - timedelta(days=1)
    return last_of_previous.month, last_of_previous.year


def format_month_label(month: int, year: int) -> str:
    """Format a month/year as MM_YYYY."""
    return f"{month:02d}_{year:04d}"


def authenticate_google(service_account_json: str):
    """Create an authorized gspread client from a JSON string."""
    info = json.loads(service_account_json)
    return gspread.service_account_from_dict(info, scopes=GOOGLE_SCOPES)


def load_station_names(path: str = "stations.json") -> set[str]:
    """Load the set of known station names from the local JSON file."""
    with open(path, encoding="utf-8") as file:
        stations = json.load(file)
    return {station["name"] for station in stations}


def sheet_base_name(title: str) -> str:
    """Strip the trailing _MM_YYYY suffix from a sheet title."""
    match = SUFFIX_PATTERN.search(title)
    if match:
        return title[: match.start()]
    return title


def find_month_sheets(spreadsheet, month_label: str):
    """Return all worksheets whose titles end with _MM_YYYY."""
    suffix = f"_{month_label}"
    return [worksheet for worksheet in spreadsheet.worksheets() if worksheet.title.endswith(suffix)]


def categorize_sheets(sheets, station_names: set[str]) -> tuple[list, list]:
    """Split sheets into employee sheets and station sheets."""
    employees = []
    stations = []
    for worksheet in sheets:
        base = sheet_base_name(worksheet.title)
        if base.startswith("U ") or base in station_names:
            stations.append(worksheet)
        else:
            employees.append(worksheet)
    return sorted(employees, key=lambda ws: ws.title), sorted(stations, key=lambda ws: ws.title)


def worksheet_to_dataframe(worksheet) -> pd.DataFrame:
    """Convert a gspread worksheet into a pandas DataFrame."""
    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()
    header, *rows = values
    return pd.DataFrame(rows, columns=header)


def excel_safe_sheet_name(name: str, existing_names: set[str] | None = None) -> str:
    """Return an Excel-compatible sheet name, avoiding duplicates."""
    existing_names = existing_names or set()
    safe = re.sub(r'[\\/*?:\[\]]', "_", name)
    if len(safe) > 31:
        safe = safe[:31]

    candidate = safe
    counter = 1
    while candidate in existing_names:
        suffix = f"_{counter}"
        candidate = safe[: 31 - len(suffix)] + suffix
        counter += 1

    return candidate


def write_sheets_to_excel(sheets, output_path: Path) -> None:
    """Write a list of worksheets to a single Excel workbook."""
    used_names: set[str] = set()
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for worksheet in sheets:
            dataframe = worksheet_to_dataframe(worksheet)
            tab_name = excel_safe_sheet_name(sheet_base_name(worksheet.title), used_names)
            used_names.add(tab_name)
            dataframe.to_excel(writer, sheet_name=tab_name, index=False)


def send_document_via_telegram(bot_token: str, chat_id: str, file_path: Path, caption: str) -> dict:
    """Send a local file as a document via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(url, data=data, files=files, timeout=60)
    response.raise_for_status()
    return response.json()


def build_output_path(month_label: str) -> Path:
    """Return the path for the monthly report Excel file."""
    return Path(f"Monatsbericht_{month_label}.xlsx")


def main() -> None:
    """Generate the previous month's report and send it via Telegram."""
    config = load_config()
    month, year = get_previous_month()
    month_label = format_month_label(month, year)

    client = authenticate_google(config["google_service_account_json"])
    spreadsheet = client.open_by_key(config["spreadsheet_id"])
    month_sheets = find_month_sheets(spreadsheet, month_label)

    if not month_sheets:
        raise ValueError(f"No worksheets found for month {month_label}")

    station_names = load_station_names()
    employee_sheets, station_sheets = categorize_sheets(month_sheets, station_names)
    ordered_sheets = employee_sheets + station_sheets

    output_path = build_output_path(month_label)
    write_sheets_to_excel(ordered_sheets, output_path)

    caption = f"Monatsbericht {month_label}"
    send_document_via_telegram(
        config["telegram_bot_token"],
        config["telegram_chat_id"],
        output_path,
        caption,
    )
    logger.info("Monthly report %s sent successfully.", output_path)


if __name__ == "__main__":
    main()
