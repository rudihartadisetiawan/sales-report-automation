"""Write dummy sales CSV to Google Sheets."""
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ponytail: one shared retry helper, covers both Sheets and Gmail later
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = os.environ.get("SHEET_ID", "142MGSBlInlhRWYp_TzPlWetVQ3nQc-wJplGAmE67a6A")
CREDS_FILE = os.environ.get("CREDS_FILE", "service-account-key.json")
CSV_FILE = "data/dummy_sales.csv"


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "write_to_sheet.log")
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # Also stream to stdout so it is visible in runs
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def get_service(creds_file: str, scopes: list):
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=scopes
    )
    return build("sheets", "v4", credentials=credentials)


def call_with_retry(func, max_retries: int = 3):
    """Call a Sheets API function with exponential backoff."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except HttpError as e:
            last_error = e
            if e.resp.status in (429, 500, 503):
                wait = 2 ** attempt
                logging.warning(f"API attempt {attempt} failed, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise
    raise last_error


def write_to_sheet(service, sheet_id: str, df: pd.DataFrame) -> None:
    # Clear existing sheet content
    sheet = service.spreadsheets()
    range_name = "Sheet1"
    call_with_retry(lambda: sheet.values().clear(spreadsheetId=sheet_id, range=range_name, body={}).execute())

    # Prepare values: header + rows
    values = [df.columns.tolist()] + df.values.tolist()
    body = {"values": values}
    call_with_retry(
        lambda: sheet.values().update(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
    )


def read_first_rows(service, sheet_id: str, rows: int = 5) -> list:
    sheet = service.spreadsheets()
    range_name = f"Sheet1!A1:F{rows}"
    result = call_with_retry(
        lambda: sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    )
    return result.get("values", [])


def main() -> None:
    setup_logging()
    logging.info("Starting write_to_sheet.py")

    if not os.path.exists(CSV_FILE):
        logging.error(f"CSV file not found: {CSV_FILE}")
        sys.exit(1)
    if not os.path.exists(CREDS_FILE):
        logging.error(f"Service account key not found: {CREDS_FILE}")
        sys.exit(1)

    df = pd.read_csv(CSV_FILE)
    service = get_service(CREDS_FILE, SCOPES)
    write_to_sheet(service, SHEET_ID, df)
    logging.info(f"Wrote {len(df)} rows to Google Sheets")

    # Verification: read first 5 rows back and compare with CSV
    sheet_rows = read_first_rows(service, SHEET_ID, rows=6)
    csv_rows = [df.columns.tolist()] + df.head(5).values.tolist()

    print("\n--- Verification: first 5 rows in sheet ---")
    for row in sheet_rows:
        print(row)

    # Compare as strings because Sheets API returns all values as strings
    csv_rows_str = [[str(cell) for cell in row] for row in csv_rows]
    if sheet_rows == csv_rows_str:
        logging.info("Verification OK: sheet data matches CSV")
    else:
        logging.warning("Verification mismatch between sheet and CSV")


if __name__ == "__main__":
    main()
