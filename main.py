"""SalesPulse — Automated Weekly Sales Report pipeline.

Reads sales data from Google Sheets → analyses → generates chart + HTML email → sends via Gmail.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backend.read_sheet import read_sales_data
from backend.analysis import compute_wow_comparison, compute_weekly_report, format_report
from backend.mailer import send_email
from frontend.email_template import build_email_html, build_subject, generate_chart

# ---------------------------------------------------------------------------
# ponytail: single setup_logging shared by the pipeline
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).resolve().parent / "logs"
OUT_DIR = Path(__file__).resolve().parent / "frontend" / "out"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Data bridge: analysis output → email_template input
# ---------------------------------------------------------------------------
def _build_frontend_data(
    df: pd.DataFrame, wow: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Transform analysis/wow output into the shapes email_template expects."""
    current = wow["current_week"]

    # Filter the DataFrame to current week for per-product detail (incl. category)
    ws = current["week_start"]
    we = current["week_end"]
    mask = (df["tanggal"].dt.date >= ws) & (df["tanggal"].dt.date <= we)
    week_df = df.loc[mask]

    # Aggregate per product
    products = (
        week_df.groupby(["nama_produk", "kategori"], as_index=False)
        .agg({"jumlah_terjual": "sum", "total": "sum"})
        .sort_values("total", ascending=False)
        .to_dict(orient="records")
    )

    weekly_data = {
        "products": products,
        "total_revenue": current["total_value"],
        "total_units": current["total_units"],
        "week_start_date": ws.strftime("%d %b %Y") if isinstance(ws, date) else str(ws),
        "week_end_date": we.strftime("%d %b %Y") if isinstance(we, date) else str(we),
    }

    wow_data = {"revenue_wow_pct": wow["change_pct"]["value_change_pct"]}

    return weekly_data, wow_data


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline() -> None:
    setup_logging()
    logging.info("=== SalesPulse pipeline started ===")

    sheet_id = os.environ.get("SHEET_ID", "142MGSBlInlhRWYp_TzPlWetVQ3nQc-wJplGAmE67a6A")
    creds_file = os.environ.get("CREDS_FILE", "service-account-key.json")

    if not os.path.exists(creds_file):
        logging.error("Service account key not found: %s", creds_file)
        sys.exit(1)

    # 1. Read data
    logging.info("Step 1/5 — Reading data from Google Sheets...")
    df = read_sales_data(sheet_id, creds_file)
    logging.info("Read %d rows, date range %s to %s", len(df), df["tanggal"].min().date(), df["tanggal"].max().date())

    # 2. Analyse
    logging.info("Step 2/5 — Computing weekly report & WoW comparison...")
    weekly = compute_weekly_report(df)
    wow = compute_wow_comparison(df)
    text_report = format_report(weekly, wow)
    logging.info("Report:\n%s", text_report)

    # 3. Generate chart + email
    logging.info("Step 3/5 — Building email HTML & chart...")
    weekly_data, wow_data = _build_frontend_data(df, wow)
    chart_path = str(OUT_DIR / "chart.png")
    generate_chart(weekly_data, chart_path)

    html_body = build_email_html(weekly_data, wow_data, chart_path)
    week_end = weekly["week_end"]
    subject = build_subject(wow_data, week_end)

    # 4. Send email
    logging.info("Step 4/5 — Sending email...")
    sender_email = os.environ.get("SENDER_EMAIL")
    to_email = os.environ.get("TO_EMAIL")

    if not sender_email or not to_email:
        logging.warning("SENDER_EMAIL or TO_EMAIL not set — skipping send. Set env vars to enable.")
        logging.info("Pipeline finished (dry run — no email sent).")
        return

    send_email(
        to_email=to_email,
        subject=subject,
        html_body=html_body,
        chart_path=chart_path,
    )

    # 5. Done
    logging.info("Step 5/5 — Complete! Email sent to %s", to_email)


if __name__ == "__main__":
    run_pipeline()
