"""SalesPulse weekly sales report — email HTML + chart generation.

Ponytail: one module, stdlib + matplotlib only. Inline CSS for email client
compatibility. Theme palette is module-level constants so chart and HTML
stay in sync without a config object.
"""
from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")  # ponytail: headless backend, no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# --- SalesPulse visual identity ----------------------------------------------
# Modern teal/coral palette — deliberately NOT matplotlib defaults.
TEAL = "#0F7B7B"          # primary
TEAL_DARK = "#0A5757"
TEAL_SOFT = "#E6F2F2"
CORAL = "#E8745A"         # accent / negative delta
CORAL_SOFT = "#FBE9E3"
INK = "#1F2A33"           # body text
MUTED = "#5C6B75"
BG = "#F4F7F8"            # page background
CARD = "#FFFFFF"
LINE = "#E2E8EA"

# ponytail: one font family for chart + email; DejaVu Sans ships with matplotlib
FONT_FAMILY = "DejaVu Sans"


# --- Chart --------------------------------------------------------------------
def generate_chart(weekly_data: dict[str, Any], output_path: str) -> str:
    """Render horizontal bar chart of top-5 products by revenue.

    weekly_data expected shape:
        {"products": [{"nama_produk", "kategori", "jumlah_terjual", "total"}, ...]}
    Returns absolute path to the saved PNG.
    """
    products = sorted(
        weekly_data.get("products", []),
        key=lambda p: p.get("total", 0),
        reverse=True,
    )[:5]
    if not products:
        raise ValueError("weekly_data['products'] is empty")

    names = [p["nama_produk"] for p in products][::-1]  # reverse so top is on top
    totals = [p["total"] for p in products][::-1]

    plt.rcParams.update({
        "font.family": FONT_FAMILY,
        "font.size": 11,
        "axes.edgecolor": LINE,
        "axes.linewidth": 0.8,
    })

    fig, ax = plt.subplots(figsize=(6, 4), dpi=130)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD)

    bars = ax.barh(names, totals, color=TEAL, edgecolor="none", height=0.62)
    # Highlight the #1 product in coral
    if bars:
        bars[-1].set_color(CORAL)

    ax.set_xlabel("Revenue (Rp)", color=MUTED, fontsize=10)
    ax.set_title("Top 5 Products — This Week", color=INK, fontsize=13, pad=12, loc="left")

    ax.tick_params(colors=MUTED, length=0)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(LINE)
    ax.spines["bottom"].set_color(LINE)

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x/1000)}k"))
    ax.grid(axis="x", color=LINE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    # Value labels at bar ends
    xmax = max(totals) if totals else 1
    for bar, val in zip(bars, totals):
        ax.text(bar.get_width() + xmax * 0.01, bar.get_y() + bar.get_height() / 2,
                f"Rp{val:,.0f}", va="center", ha="left", color=INK, fontsize=9)

    ax.set_xlim(0, xmax * 1.18)
    plt.tight_layout()

    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    fig.savefig(abs_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return abs_path


# --- HTML ---------------------------------------------------------------------
def _fmt_rp(n: float) -> str:
    return f"Rp{n:,.0f}"


def _delta_badge(pct: float) -> str:
    """WoW change badge. Positive=teal, negative=coral."""
    if pct >= 0:
        color, bg, arrow, word = TEAL, TEAL_SOFT, "▲", "up"
    else:
        color, bg, arrow, word = CORAL, CORAL_SOFT, "▼", "down"
    return (
        f'<span style="display:inline-block;background:{bg};color:{color};'
        f'font-size:12px;font-weight:600;padding:4px 10px;border-radius:6px;">'
        f'{arrow} {abs(pct):.1f}% {word}</span>'
    )


def _card(label: str, value: str, badge: str = "") -> str:
    badge_html = f'<div style="margin-top:8px;">{badge}</div>' if badge else ""
    return f"""<td style="width:33.33%;padding:0 6px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
             style="background:{CARD};border:1px solid {LINE};border-radius:10px;">
        <tr><td style="padding:18px 16px;">
          <div style="font-size:11px;color:{MUTED};text-transform:uppercase;
                      letter-spacing:0.06em;">{label}</div>
          <div style="font-size:22px;font-weight:700;color:{INK};margin-top:6px;
                      font-family:{FONT_FAMILY},Arial,sans-serif;">{value}</div>
          {badge_html}
        </td></tr>
      </table>
    </td>"""


def build_email_html(weekly_data: dict[str, Any], wow_data: dict[str, Any],
                     chart_path: str) -> str:
    """Compose full HTML email body. Inline CSS, table layout, max-width 600px."""
    total_rev = weekly_data.get("total_revenue", 0)
    total_units = weekly_data.get("total_units", 0)
    wow_rev_pct = wow_data.get("revenue_wow_pct", 0.0)

    products = sorted(
        weekly_data.get("products", []),
        key=lambda p: p.get("total", 0),
        reverse=True,
    )[:5]

    # Category performance
    cat_map: dict[str, dict[str, float]] = {}
    for p in weekly_data.get("products", []):
        c = p["kategori"]
        d = cat_map.setdefault(c, {"units": 0, "revenue": 0.0})
        d["units"] += p.get("jumlah_terjual", 0)
        d["revenue"] += p.get("total", 0)
    categories = sorted(cat_map.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    cat_max_rev = max((v["revenue"] for _, v in categories), default=1)

    # Chart image — embed as base64 data URI for portability (also works with CID
    # via compose_email; here we inline so the HTML preview is self-contained).
    chart_cid = "cid:salespulse_chart"
    _ = chart_path  # referenced by caller for CID attachment

    # --- Top 5 products rows
    prod_rows = ""
    for i, p in enumerate(products, start=1):
        rank_color = CORAL if i == 1 else TEAL
        prod_rows += f"""<tr>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{INK};
                     font-weight:600;">{i}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{INK};
                     font-weight:600;">{p['nama_produk']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{MUTED};
                     font-size:12px;">{p['kategori']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{MUTED};
                     text-align:right;">{p['jumlah_terjual']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{INK};
                     font-weight:600;text-align:right;">{_fmt_rp(p['total'])}</td>
        </tr>"""

    # --- Category rows with mini bar
    cat_rows = ""
    for name, d in categories:
        pct_w = int((d["revenue"] / cat_max_rev) * 100) if cat_max_rev else 0
        cat_rows += f"""<tr>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{INK};
                     font-weight:600;">{name}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{MUTED};
                     text-align:right;">{d['units']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};color:{INK};
                     font-weight:600;text-align:right;">{_fmt_rp(d['revenue'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid {LINE};width:120px;">
            <div style="background:{TEAL_SOFT};border-radius:4px;height:8px;">
              <div style="background:{TEAL};height:8px;border-radius:4px;width:{pct_w}%;"></div>
            </div>
          </td>
        </tr>"""

    week_end = weekly_data.get("week_end_date", "")
    week_start = weekly_data.get("week_start_date", "")

    return f"""<!DOCTYPE html>
<html lang="id">
<head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SalesPulse Weekly Report</title></head>
<body style="margin:0;padding:0;background:{BG};font-family:{FONT_FAMILY},Arial,sans-serif;
             color:{INK};">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};">
<tr><td align="center" style="padding:24px 12px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px;width:100%;background:{BG};">

  <!-- Header / branding -->
  <tr><td style="padding:8px 0 16px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="vertical-align:middle;">
          <span style="font-size:20px;font-weight:700;color:{TEAL_DARK};
                       letter-spacing:-0.01em;">SalesPulse</span>
          <span style="font-size:11px;color:{MUTED};margin-left:8px;">Weekly Sales Report</span>
        </td>
        <td align="right" style="vertical-align:middle;">
          <span style="font-size:12px;color:{MUTED};">{week_start} — {week_end}</span>
        </td>
      </tr>
    </table>
    <div style="height:3px;background:{TEAL};border-radius:2px;margin-top:10px;"></div>
  </td></tr>

  <!-- Highlight cards -->
  <tr><td>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr>
        {_card("Total Revenue", _fmt_rp(total_rev), _delta_badge(wow_rev_pct))}
        {_card("Total Units", f"{total_units:,}", "")}
        {_card("Top Product", products[0]['nama_produk'] if products else '-', "")}
      </tr>
    </table>
  </td></tr>

  <!-- Chart -->
  <tr><td style="padding:20px 0 8px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{CARD};border:1px solid {LINE};border-radius:10px;">
      <tr><td style="padding:16px;">
        <img src="{chart_cid}" alt="Top 5 Products chart"
             width="568" style="display:block;width:100%;max-width:568px;height:auto;
             border-radius:6px;"/>
      </td></tr>
    </table>
  </td></tr>

  <!-- Top 5 products -->
  <tr><td style="padding:20px 0 0 0;">
    <div style="font-size:14px;font-weight:700;color:{INK};margin-bottom:8px;
                padding-left:2px;">Top 5 Products</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{CARD};border:1px solid {LINE};border-radius:10px;
                  border-collapse:collapse;">
      <tr style="background:{TEAL_SOFT};">
        <th style="padding:10px 12px;text-align:left;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">#</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Product</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Category</th>
        <th style="padding:10px 12px;text-align:right;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Units</th>
        <th style="padding:10px 12px;text-align:right;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Revenue</th>
      </tr>
      {prod_rows}
    </table>
  </td></tr>

  <!-- Category performance -->
  <tr><td style="padding:20px 0 0 0;">
    <div style="font-size:14px;font-weight:700;color:{INK};margin-bottom:8px;
                padding-left:2px;">Category Performance</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{CARD};border:1px solid {LINE};border-radius:10px;
                  border-collapse:collapse;">
      <tr style="background:{TEAL_SOFT};">
        <th style="padding:10px 12px;text-align:left;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Category</th>
        <th style="padding:10px 12px;text-align:right;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Units</th>
        <th style="padding:10px 12px;text-align:right;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Revenue</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;color:{TEAL_DARK};
                   text-transform:uppercase;letter-spacing:0.05em;">Share</th>
      </tr>
      {cat_rows}
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:24px 0 8px 0;">
    <div style="height:1px;background:{LINE};margin-bottom:14px;"></div>
    <p style="margin:0;font-size:11px;color:{MUTED};line-height:1.5;">
      Report generated by <strong style="color:{TEAL_DARK};">SalesPulse</strong>.
      Data sourced from your Google Sheets sales log.<br/>
      Questions or want to adjust the report? Just reply to this email.
    </p>
  </td></tr>

</table>

</td></tr>
</table>
</body>
</html>"""


# --- Subject -----------------------------------------------------------------
def build_subject(wow_data: dict[str, Any], week_end_date: str | datetime) -> str:
    """Informatif + spesifik: sertakan arah & magnitudo WoW revenue."""
    pct = wow_data.get("revenue_wow_pct", 0.0)
    direction = "up" if pct >= 0 else "down"
    if isinstance(week_end_date, datetime):
        date_str = week_end_date.strftime("%d %b %Y")
    else:
        date_str = str(week_end_date)
    return f"📊 Weekly Sales Report — Week ending {date_str}: Revenue {direction} {abs(pct):.1f}%"


# --- Compose -----------------------------------------------------------------
def compose_email(weekly_data: dict[str, Any], wow_data: dict[str, Any],
                  chart_path: str) -> dict[str, Any]:
    """Bundle subject + html + chart path for the backend sender."""
    week_end = weekly_data.get("week_end_date", datetime.now())
    return {
        "subject": build_subject(wow_data, week_end),
        "html_body": build_email_html(weekly_data, wow_data, chart_path),
        "chart_path": os.path.abspath(chart_path),
    }


# --- Self-check / demo --------------------------------------------------------
def _demo() -> None:
    """Ponytail self-check: build a chart + HTML from dummy data, write files."""
    dummy_products = [
        {"nama_produk": "Sneakers", "kategori": "Fashion", "jumlah_terjual": 48, "total": 15_360_000},
        {"nama_produk": "Power Bank 10000mAh", "kategori": "Elektronik", "jumlah_terjual": 35, "total": 8_575_000},
        {"nama_produk": "Headset Bluetooth", "kategori": "Elektronik", "jumlah_terjual": 30, "total": 5_550_000},
        {"nama_produk": "Tas Ransel", "kategori": "Fashion", "jumlah_terjual": 28, "total": 5_460_000},
        {"nama_produk": "Kemeja Flanel", "kategori": "Fashion", "jumlah_terjual": 25, "total": 4_125_000},
        {"nama_produk": "Set Pisau Dapur", "kategori": "Rumah Tangga", "jumlah_terjual": 18, "total": 2_610_000},
        {"nama_produk": "Kipas Angin Meja", "kategori": "Elektronik", "jumlah_terjual": 15, "total": 2_325_000},
        {"nama_produk": "Botol Minum 1L", "kategori": "Rumah Tangga", "jumlah_terjual": 22, "total": 1_430_000},
    ]
    weekly = {
        "products": dummy_products,
        "total_revenue": sum(p["total"] for p in dummy_products),
        "total_units": sum(p["jumlah_terjual"] for p in dummy_products),
        "week_start_date": "2026-07-21",
        "week_end_date": "2026-07-27",
    }
    wow = {"revenue_wow_pct": 12.4}

    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    chart_path = os.path.join(out_dir, "chart.png")

    generate_chart(weekly, chart_path)
    email = compose_email(weekly, wow, chart_path)

    html_path = os.path.join(out_dir, "preview.html")
    # For preview, swap CID for a file:// ref so it opens in a browser
    preview_html = email["html_body"].replace("cid:salespulse_chart",
                                              "file://" + chart_path.replace("\\", "/"))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(preview_html)

    # ponytail: Windows terminal may not support emoji; replace on encode failure
    def _safe_print(label, value):
        try:
            print(f"{label}: {value}")
        except UnicodeEncodeError:
            print(f"{label}: {value.encode('ascii', errors='replace').decode('ascii')}")

    _safe_print("Subject", email["subject"])
    _safe_print("Chart  ", chart_path)
    _safe_print("HTML   ", html_path)
    print("HTML bytes:", len(email["html_body"]))

    # Sanity assertions
    assert "SalesPulse" in email["html_body"]
    assert "cid:salespulse_chart" in email["html_body"]
    assert os.path.getsize(chart_path) > 1000
    assert "Revenue" in email["subject"] and "12.4%" in email["subject"]
    print("OK — self-check passed")


if __name__ == "__main__":
    _demo()