# AGENTS.md — Automated Weekly Sales Report

Dibaca oleh semua subagent di awal tiap sesi. Detail lengkap requirement ada di `PRD.md`, status progres di `PROGRESS.md`.

## Arsitektur Agent

- **Manager** — orkestrasi task, breakdown kerja ke subagent, review integrasi akhir
- **Backend** — koneksi Google Sheets API, pengolahan data (pandas), pengiriman via Gmail API, scheduler
- **Frontend** — desain email HTML (bukan dashboard di project ini), styling grafik
- **Security** — credential handling (service account, Gmail API scope), review sebelum deploy

## Pemilihan Model per Jenis Tugas

Sama seperti project pertama, sesuaikan model ke kompleksitas tugas.

| Jenis tugas | Contoh konkret | Model |
|---|---|---|
| Boilerplate & tugas rutin | Setup struktur folder, baca data Sheets, format dataframe | `opencode-go/deepseek-v4-flash` |
| Logika bisnis & implementasi | Perhitungan ringkasan, integrasi Gmail API, generate grafik | `opencode-go/kimi-k2.7-code` |
| Styling email/visual | Desain HTML email, styling grafik matplotlib/plotly | `opencode-go/glm-5.2` |
| Keputusan arsitektur & security review | Desain alur credential, review sebelum deploy, keputusan scope | `opencode-go/deepseek-v4-pro` (manager) / `opencode-go/qwen3.7-max` (security) |

## Aturan Umum (Semua Agent)

1. **Ikuti PRD.md sebagai sumber kebenaran scope.** Jangan menambah fitur di luar scope MVP (lihat Bagian 5 PRD) tanpa konfirmasi.
2. **Kode minimal, tidak over-engineered.**
3. **Update PROGRESS.md di akhir sesi.**
4. **Session handoff:** baca PROGRESS.md di awal sesi sebelum mulai kerja.

## Aturan Khusus Backend

- Autentikasi Google Sheets & Gmail pakai **service account**, bukan OAuth user flow — supaya bisa jalan otomatis tanpa login manual tiap eksekusi.
- Scope Gmail API dibatasi seminimal mungkin (hanya `gmail.send`, tidak butuh akses baca inbox).
- Setiap run harus tercatat di log (waktu, status, ringkasan singkat) — jangan gagal senyap.
- Retry logic untuk pemanggilan API eksternal (Sheets & Gmail).

## Aturan Khusus Frontend

- **Email tidak boleh terlihat seperti notifikasi generik.** Wajib baca Bagian 6 PRD.md sebelum mulai styling.
- Grafik wajib di-style ulang (warna, font) — jangan pakai default matplotlib/plotly tanpa penyesuaian.
- Subjek email harus informatif dan spesifik (sertakan angka kunci), bukan judul generik.
- Uji tampilan email di lebih dari satu klien email jika memungkinkan (Gmail web minimal), karena rendering HTML email sering berbeda dari HTML biasa.

## Aturan Khusus Security

- Service account JSON key **tidak boleh** ter-commit ke git — pastikan masuk `.gitignore`, disimpan sebagai GitHub Secret untuk GitHub Actions.
- Scope API (Sheets & Gmail) di-review supaya seminimal mungkin — prinsip least privilege.
- Tidak ada data pribadi/PII pihak ketiga yang ikut ter-log atau ter-expose di repository publik.
- Review alamat email tujuan tidak hardcoded di kode — pakai environment variable.

## Batas Scope (Ringkas dari PRD Bagian 5)

Jangan implementasi tanpa diminta: dashboard web interaktif, multi-tenant, integrasi POS/e-commerce real-time, analitik prediktif/ML. Semua ini di luar scope project ini.
