"""Read sales data from Google Sheets and print a summary."""
import os
import sys

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def read_sales_data(sheet_id: str, creds_file: str) -> pd.DataFrame:
    """Read the sales data from the first sheet and return a DataFrame."""
    credentials = service_account.Credentials.from_service_account_file(
        creds_file, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range="Sheet1").execute()
    values = result.get("values", [])
    if not values:
        raise ValueError("No data found in sheet")
    df = pd.DataFrame(values[1:], columns=values[0])
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df["jumlah_terjual"] = pd.to_numeric(df["jumlah_terjual"], errors="coerce")
    df["harga_satuan"] = pd.to_numeric(df["harga_satuan"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print a concise summary of the sales data."""
    total_rows = len(df)
    date_min = df["tanggal"].min().date()
    date_max = df["tanggal"].max().date()
    total_revenue = int(df["total"].sum())
    total_units = int(df["jumlah_terjual"].sum())
    top_products = (
        df.groupby("nama_produk")["jumlah_terjual"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    print("\n=== Sales Data Summary ===")
    print(f"Total rows: {total_rows}")
    print(f"Date range: {date_min} to {date_max}")
    print(f"Total units sold: {total_units}")
    print(f"Total revenue: Rp {total_revenue:,}")
    print("\nTop 5 products by units sold:")
    for idx, (product, units) in enumerate(top_products.items(), 1):
        print(f"  {idx}. {product}: {units} units")


def main() -> None:
    sheet_id = os.environ.get("SHEET_ID", "142MGSBlInlhRWYp_TzPlWetVQ3nQc-wJplGAmE67a6A")
    creds_file = os.environ.get("CREDS_FILE", "service-account-key.json")

    if not os.path.exists(creds_file):
        print(f"Service account key not found: {creds_file}", file=sys.stderr)
        sys.exit(1)

    df = read_sales_data(sheet_id, creds_file)
    print_summary(df)


if __name__ == "__main__":
    main()
