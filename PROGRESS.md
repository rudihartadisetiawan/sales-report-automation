# PROGRESS.md — Automated Weekly Sales Report

## Status

**Fase 2 selesai + email terkirim** — Processing, email design, Gmail OAuth2 integration, pipeline orkestrasi, end-to-end test sukses.

## Done

- [x] `.gitignore` — melindungi `service-account-key.json`, `client_secret.json`, `gmail_token.json`, `__pycache__`, `.env`, `*.log`, `venv/`, `frontend/out/`.
- [x] `backend/generate_dummy_data.py` — generate 630 baris data dummy 6 minggu (42 hari), 12 produk, 4 kategori.
- [x] `data/dummy_sales.csv` — CSV output dari generator.
- [x] `backend/write_to_sheet.py` — baca CSV, autentikasi service account, tulis ke Sheets, retry 3x, logging, verifikasi baca ulang.
- [x] `backend/read_sheet.py` — modul baca sheet, return DataFrame, print summary.
- [x] `requirements.txt` — dependensi: google-auth, google-auth-oauthlib, google-api-python-client, pandas, numpy, matplotlib.
- [x] `backend/analysis.py` — modul analisis mingguan: `compute_weekly_report`, `compute_wow_comparison`, `format_report`. Run standalone, log ke `logs/analysis.log`.
- [x] `frontend/email_template.py` — SalesPulse-branded HTML email + styled matplotlib chart (teal/coral palette). `generate_chart`, `build_email_html`, `build_subject`, `compose_email`, self-check demo.
- [x] `backend/oauth_setup.py` — one-time OAuth2 browser consent, simpan refresh token ke `gmail_token.json`. Untuk akun @gmail.com.
- [x] `backend/mailer.py` — Gmail API sender, dual auth:
  - **OAuth2** (prioritas utama): load `gmail_token.json`, auto-refresh token. Works with @gmail.com.
  - **Service account** (fallback): domain-wide delegation. Works with Google Workspace.
  - Scope `gmail.send` only, retry 3x, inline chart via CID, logging ke `logs/mailer.log`.
- [x] `main.py` — pipeline orkestrasi end-to-end: read → analyse → chart → email → send. Data bridge between analysis output and email template input. Dry-run safe (skip send when `SENDER_EMAIL`/`TO_EMAIL` not set).
- [x] **Security review Fase 2** — credential handling PASS, scope API minimal (`gmail.send`, `spreadsheets.readonly`), email addresses via env vars, no hardcoded secrets, no PII in logs. OAuth client secret & token file in `.gitignore`.

## Verified

- Write ke Google Sheets: 630 rows written, verifikasi 5 baris pertama **match** CSV.
- `read_sheet.py` summary: 630 rows, 2026-06-17 s/d 2026-07-28, revenue Rp 433,917,111, 2,550 units sold.
- `analysis.py`: computed weekly report (2026-07-27 to 2026-08-02), WoW comparison, top 5 products, category performance. Output validated.
- `email_template.py` self-check: chart PNG (39 KB), HTML preview (13 KB), assertions passed.
- `mailer.py` credential resolution: OAuth2 token exists → OAuth2 priority ✅. No token → service account fallback ✅. Neither → clear error ✅.
- `main.py` end-to-end dry run: all 5 steps execute, logs to `logs/pipeline.log`.
- **End-to-end email send**: OAuth2 credentials → Gmail API → email terkirim ke `rudihartadi58@gmail.com` (message id `19fa81d389261815`).
- Security review: **AMAN**.

## Next

- [ ] GitHub Actions scheduler untuk Senin pagi.
- [ ] README + case study + screenshot email.
- [ ] `git init` + initial commit.

## Notes

- Service account key tetap di root dan **tidak di-commit** (dilindungi `.gitignore`).
- `client_secret.json` (OAuth Desktop) dan `gmail_token.json` (refresh token) juga di `.gitignore`.
- Gmail scope: `gmail.send` only — minimal, sesuai prinsip least privilege.
- Sheets scope: read-only di `read_sheet.py`, write hanya di `write_to_sheet.py` (seeding).
- CID reference: `salespulse_chart` — konsisten antara `mailer.py` dan `email_template.py`.
- Data shape bridge ada di `main.py:_build_frontend_data()` — transform analysis output ke format email template input.
