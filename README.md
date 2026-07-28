# SalesPulse — Automated Weekly Sales Report

> **"Your sales data, delivered to your inbox every Monday morning — zero manual work."**

SalesPulse reads sales transactions from a Google Sheet, crunches the numbers, and sends a clean, branded email report with charts — automatically, every week. Built as a portfolio project for freelance automation/API integration work targeting small businesses (UMKM/toko online).

---

## 📸 Sample Email

<p align="center">
  <img src="docs/email-screenshot.png" alt="SalesPulse weekly report email" width="500"/>
  <br/><em>SalesPulse email report — highlight cards, top products chart, category breakdown</em>
</p>

> ⚠️ Replace `docs/email-screenshot.png` with an actual screenshot from your inbox.

---

## 🎯 The Problem

Small online stores track sales in spreadsheets but rarely turn that data into actionable reports. The owner opens the sheet on Monday, manually sums columns, maybe copy-pastes into WhatsApp — or just skips it because "no time."

**SalesPulse eliminates that manual work entirely.** Once set up, it reads the same Google Sheet, computes the weekly snapshot, and delivers it straight to email. No dashboard to check, no button to click.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Google Sheets   │────▶│  Python Pipeline  │────▶│  Gmail Inbox     │
│  (sales log)     │     │  (GitHub Actions) │     │  (report email)  │
└─────────────────┘     └──────────────────┘     └──────────────────┘
         │                       │
         │  Service Account       │  OAuth2 Refresh Token
         │  (read-only)           │  (gmail.send scope)
         │                       │
    ┌────▼────┐             ┌────▼────┐
    │  Sheets  │             │  Gmail  │
    │   API    │             │   API   │
    └─────────┘             └─────────┘
```

| Layer | Tool | Detail |
|---|---|---|
| Data source | Google Sheets API | Service account, read-only scope |
| Processing | Python + pandas | Weekly aggregation, WoW comparison, category ranking |
| Visualization | matplotlib | Styled bar chart (teal/coral palette), 600×400px |
| Email delivery | Gmail API | OAuth2 refresh token (works with @gmail.com), `gmail.send` scope only |
| Scheduler | GitHub Actions | Cron: every Monday 07:00 WIB (00:00 UTC) |
| Secrets | GitHub Secrets | Credential files never touch the repo |

---

## 📊 Report Contents

Every Monday email includes:

- **Revenue & units** — current week totals with week-over-week % change
- **Top 5 products** — ranked by units sold, with revenue per product
- **Category performance** — revenue breakdown with inline progress bars
- **Styled bar chart** — top products visualization (embedded in email)

Subject line example: `📊 Weekly Sales Report — Week ending 02 Aug 2026: Revenue down 74.3%`

---

## 🔐 Security

- **Least privilege scopes:** Sheets `readonly`, Gmail `send` only (no inbox access)
- **Zero hardcoded secrets:** all credentials via environment variables / GitHub Secrets
- **No PII exposure:** logs contain only timestamps and aggregate numbers
- **`.gitignore` protected:** service account key, OAuth client secret, refresh token, `.env`

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud project with Sheets API + Gmail API enabled
- Gmail account (for sending) added as test user in OAuth consent screen

### 1. Clone & install

```bash
git clone <repo-url>
cd salespulse
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. Google Sheets setup

1. Create a service account, download JSON key → save as `service-account-key.json`
2. Share your Google Sheet with the service account email (Editor access)
3. Add sales data with columns: `tanggal, nama_produk, kategori, jumlah_terjual, harga_satuan, total`

Or generate dummy data:

```bash
python backend/generate_dummy_data.py   # creates data/dummy_sales.csv
python backend/write_to_sheet.py        # uploads to Sheets
```

### 3. Gmail OAuth2 setup (one-time)

```bash
# Place your OAuth Desktop client JSON as client_secret.json
python backend/oauth_setup.py
# → Browser opens → log in with sender account → grant gmail.send
# → Token saved to gmail_token.json
```

### 4. Run

```bash
$env:SENDER_EMAIL = "you@gmail.com"
$env:TO_EMAIL = "recipient@email.com"
python main.py
```

### 5. GitHub Actions (automated weekly)

Add these secrets in repo **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `SHEET_ID` | Your Google Sheet ID |
| `SENDER_EMAIL` | Sender Gmail address |
| `TO_EMAIL` | Recipient email(s), comma-separated |
| `GMAIL_TOKEN_JSON` | Full content of `gmail_token.json` |
| `SERVICE_ACCOUNT_KEY_JSON` | Full content of `service-account-key.json` |

The workflow runs every Monday 07:00 WIB automatically. Test manually via **Actions → Weekly Sales Report → Run workflow**.

---

## 📁 Project Structure

```
├── .github/workflows/weekly-report.yml   # GitHub Actions scheduler
├── backend/
│   ├── analysis.py          # Weekly aggregation, WoW comparison
│   ├── generate_dummy_data.py  # Dummy sales data generator
│   ├── mailer.py            # Gmail API sender (OAuth2 + service account)
│   ├── oauth_setup.py       # One-time OAuth2 browser consent
│   ├── read_sheet.py        # Google Sheets reader
│   └── write_to_sheet.py    # Google Sheets writer (seeding)
├── frontend/
│   ├── email_template.py    # HTML email + styled matplotlib chart
│   └── out/                 # Generated chart.png + preview.html
├── data/dummy_sales.csv     # Sample 630-row dataset
├── main.py                  # Pipeline orchestrator
└── logs/                    # Runtime logs from each module
```

---

## 🧪 Tech Decisions

| Decision | Rationale |
|---|---|
| **OAuth2 over service account for Gmail** | Service accounts cannot send from @gmail.com — only Workspace domains. OAuth2 refresh token works universally. |
| **Inline CSS, table layout for email** | Email clients strip `<link>` and have poor flexbox/grid support. Tables + inline CSS are the reliable standard. |
| **matplotlib over plotly** | Lighter dependency, sufficient for static PNG. plotly would add ~50MB for an interactive graph that email can't render. |
| **No `.env` loader library** | Environment variables are set by GitHub Actions natively. No need for `python-dotenv` in production. |
| **CID image embedding** | Inline `<img src="cid:...">` ensures the chart renders without external hosting or "display images" prompts. |

---

## 💼 Case Study: TokoOnline "Rudi Mart"

**Scenario:** Rudi runs a small online store selling electronics, fashion, and household items. He logs every sale in a Google Sheet shared with his small team. Every Monday morning, he'd open the sheet, copy numbers, calculate growth, and send a WhatsApp summary to his business partner.

**Problem:** Some weeks he'd skip the report entirely when busy. When he did it, the numbers were error-prone (manual sum). His partner wanted something more visual — "show me a chart, not just numbers."

**Solution:** SalesPulse was configured to read Rudi's existing Google Sheet (same columns, no migration needed). The OAuth2 setup took 2 minutes — open browser, log in with his Gmail, grant send access. Now every Monday at 7 AM, Rudi and his partner both receive the report in their inbox before they even start the workday.

**Result:** Zero manual work per week. The partner now opens the email instead of asking Rudi for updates. When Rudi's store grew to 3 product categories, the category breakdown section in the email immediately showed which category drove the most revenue — no extra configuration needed.

---

## 📝 License

MIT — use freely for your own projects and clients.
