"""Weekly sales report analysis."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

try:
    from .read_sheet import read_sales_data
except ImportError:  # ponytail: support running as plain script
    from read_sheet import read_sales_data


def _to_date(value: date | str | pd.Timestamp | None) -> date | None:
    """Normalize a date-like value to a Python date."""
    if value is None:
        return None
    return pd.to_datetime(value).date()


def _week_bounds(ref_date: date) -> tuple[date, date]:
    """Return Monday and Sunday for the ISO week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _weekly_metrics(df: pd.DataFrame, week_start: date, week_end: date) -> dict:
    """Aggregate sales metrics for a single Monday-Sunday week."""
    mask = (df["tanggal"].dt.date >= week_start) & (df["tanggal"].dt.date <= week_end)
    wdf = df.loc[mask]

    total_units = int(wdf["jumlah_terjual"].sum())
    total_value = int(wdf["total"].sum())

    products = (
        wdf.groupby("nama_produk")
        .agg({"jumlah_terjual": "sum", "total": "sum"})
        .rename(columns={"jumlah_terjual": "units", "total": "value"})
        .sort_values(["units", "value"], ascending=False)
        .head(5)
    )
    top_5_products = [
        (name, int(row["units"]), int(row["value"])) for name, row in products.iterrows()
    ]

    categories = (
        wdf.groupby("kategori")
        .agg({"jumlah_terjual": "sum", "total": "sum"})
        .rename(columns={"jumlah_terjual": "units", "total": "value"})
    )
    category_performance = {
        name: {"units": int(row["units"]), "value": int(row["value"])}
        for name, row in categories.iterrows()
    }

    best_category = categories["value"].idxmax() if not categories.empty else None
    worst_category = categories["value"].idxmin() if not categories.empty else None

    return {
        "week_start": week_start,
        "week_end": week_end,
        "total_units": total_units,
        "total_value": total_value,
        "top_5_products": top_5_products,
        "category_performance": category_performance,
        "best_category": best_category,
        "worst_category": worst_category,
    }


def compute_weekly_report(df: pd.DataFrame, reference_date: date | str | None = None) -> dict:
    """Build the weekly report for the week containing reference_date."""
    if reference_date is None:
        ref = df["tanggal"].max()
        if pd.isna(ref):
            raise ValueError("No valid dates found in data")
    else:
        ref = pd.to_datetime(reference_date)

    ref_date = _to_date(ref)
    week_start, week_end = _week_bounds(ref_date)
    return {
        "week_start": week_start,
        "week_end": week_end,
        "current": _weekly_metrics(df, week_start, week_end),
    }


def compute_wow_comparison(df: pd.DataFrame, reference_date: date | str | None = None) -> dict:
    """Compare current week metrics with the immediately previous week."""
    weekly = compute_weekly_report(df, reference_date)
    current = weekly["current"]

    prev_ref = current["week_start"] - timedelta(days=1)
    previous = _weekly_metrics(df, *_week_bounds(prev_ref))

    prev_units = previous["total_units"]
    prev_value = previous["total_value"]

    units_change_pct = (
        ((current["total_units"] - prev_units) / prev_units) * 100
        if prev_units
        else 0.0
    )
    value_change_pct = (
        ((current["total_value"] - prev_value) / prev_value) * 100
        if prev_value
        else 0.0
    )

    return {
        "current_week": current,
        "previous_week": previous,
        "change_pct": {
            "units_change_pct": units_change_pct,
            "value_change_pct": value_change_pct,
        },
    }


def format_report(weekly_data: dict, wow_data: dict) -> str:
    """Return a readable text summary of the weekly report."""
    current = weekly_data["current"]
    change = wow_data["change_pct"]

    def pct(value: float) -> str:
        return f"{value:+.1f}%"

    lines = [
        f"Laporan Mingguan: {weekly_data['week_start']} s/d {weekly_data['week_end']}",
        f"Total unit terjual: {current['total_units']:,} ({pct(change['units_change_pct'])})",
        f"Total revenue: Rp {current['total_value']:,} ({pct(change['value_change_pct'])})",
        "Top 5 produk:",
    ]
    for idx, (name, units, value) in enumerate(current["top_5_products"], start=1):
        lines.append(f"  {idx}. {name}: {units:,} unit, Rp {value:,}")

    lines.append("Performa kategori:")
    for category, metrics in sorted(
        current["category_performance"].items(), key=lambda kv: kv[1]["value"], reverse=True
    ):
        lines.append(
            f"  - {category}: {metrics['units']:,} unit, Rp {metrics['value']:,}"
        )

    lines.append(f"Kategori terbaik: {current['best_category']}")
    lines.append(f"Kategori terburuk: {current['worst_category']}")

    return "\n".join(lines)


def _setup_logging() -> None:
    """Configure logging to logs/analysis.log."""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "analysis.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
        force=True,
    )
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


def main() -> None:
    """Read data from Sheets, analyse, and print the report."""
    _setup_logging()

    sheet_id = os.environ.get("SHEET_ID", "142MGSBlInlhRWYp_TzPlWetVQ3nQc-wJplGAmE67a6A")
    creds_file = os.environ.get("CREDS_FILE", "service-account-key.json")

    if not os.path.exists(creds_file):
        logging.error("Service account key not found: %s", creds_file)
        sys.exit(1)

    try:
        df = read_sales_data(sheet_id, creds_file)
        weekly = compute_weekly_report(df)
        wow = compute_wow_comparison(df)
        report = format_report(weekly, wow)

        print(report)
        logging.info(
            "Report generated: %s - %s | units=%d revenue=%d",
            weekly["week_start"],
            weekly["week_end"],
            weekly["current"]["total_units"],
            weekly["current"]["total_value"],
        )
    except Exception as exc:  # pragma: no cover - keep failures visible
        logging.exception("Failed to generate report: %s", exc)
        raise


if __name__ == "__main__":
    main()
