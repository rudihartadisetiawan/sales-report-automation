# PRD.md — Automated Weekly Sales Report

## 1. Latar Belakang & Tujuan

Portofolio kedua, kategori **automation/API integration** — melengkapi kategori "scraping + analitik" (project pertama) dan "web development" (belum ada) di target skill freelance. Tujuannya menunjukkan kemampuan mengotomasi proses kerja manual berulang yang umum dibutuhkan bisnis kecil-menengah (UMKM/toko online).

**Target audiens portofolio:** klien freelance yang punya data operasional di spreadsheet tapi tidak sempat/rutin mengolahnya jadi laporan — value proposition-nya "otomasi kerjaan manual berulang", bukan "ambil data dari luar" (beda dengan project pertama).

**Skenario konkret:** setiap Senin pagi, sistem otomatis membaca data penjualan mingguan dari Google Sheets, mengolahnya jadi ringkasan (total penjualan, produk terlaris, perbandingan vs minggu lalu), lalu mengirim ringkasan itu ke email tanpa campur tangan manual.

## 2. Sumber Data

- **Google Sheets** yang dibuat sendiri sebagai simulasi data bisnis (kolom: tanggal, nama produk, kategori, jumlah terjual, harga satuan, total)
- Data diisi manual/generate dummy yang realistis untuk keperluan demo portofolio — meniru pola data penjualan toko online riil (tidak perlu data asli klien)
- Opsional: bisa juga menarik ulang sebagian data dari project pertama (eBay) sebagai variasi sumber, tapi tidak wajib

## 3. Alur Proses (Pipeline)

```
Google Sheets (data mentah, diisi manual/dummy)
    → Terjadwal mingguan (GitHub Actions, tiap Senin pagi)
    → Baca data via Google Sheets API
    → Olah data (pandas): total penjualan, produk terlaris,
      perbandingan vs minggu sebelumnya, tren kategori
    → Generate ringkasan (HTML email + grafik sederhana sebagai gambar)
    → Kirim otomatis via Gmail API
    → Log hasil kirim (sukses/gagal) untuk audit
```

## 4. Fitur Inti (Scope MVP)

1. **Koneksi ke Google Sheets** — baca data penjualan mingguan menggunakan service account (bukan OAuth user flow, supaya bisa jalan otomatis tanpa login manual tiap kali)
2. **Pengolahan data:**
   - Total penjualan (unit & nilai) minggu berjalan
   - Produk terlaris (top 5 berdasarkan unit terjual)
   - Perbandingan total penjualan vs minggu sebelumnya (naik/turun berapa persen)
   - Kategori dengan performa terbaik/terburuk
3. **Generate laporan email:**
   - Format HTML email yang didesain sengaja (bukan teks polos, bukan template default library email)
   - Sertakan 1 grafik sederhana (misal bar chart top produk) sebagai gambar inline
4. **Pengiriman otomatis** via Gmail API ke satu atau lebih alamat tujuan (dikonfigurasi via environment variable)
5. **Penjadwalan** — GitHub Actions cron, jalan tiap Senin jam tertentu (pagi waktu lokal target)
6. **Logging** — catat setiap run (waktu, status sukses/gagal, ringkasan singkat) ke file log sederhana, supaya ada jejak audit kalau ada yang gagal terkirim

## 5. Yang TIDAK Masuk Scope (Out of Scope)

- Dashboard web interaktif (project ini fokus ke laporan email, bukan dashboard — beda dengan project pertama)
- Multi-user/multi-tenant (satu sumber data, satu tujuan email untuk demo)
- Input data real-time dari sistem POS/e-commerce asli (cukup Google Sheets sebagai simulasi)
- Analitik prediktif/ML (cukup ringkasan deskriptif untuk level ini)

## 6. Kualitas Desain Email — PENTING

Email laporan **tidak boleh terlihat seperti notifikasi otomatis generik** (font default, tanpa struktur visual, plain text dengan bullet points saja). Ini bagian yang paling dilihat "klien" sebagai bukti kualitas kerja.

Yang harus dihindari:
- Email HTML tanpa styling sama sekali (hanya `<p>` dan `<br>` polos)
- Palet warna/font default seperti kebanyakan notifikasi transaksional generik
- Grafik yang di-generate tanpa styling (default matplotlib tanpa penyesuaian warna/font)

Yang harus ada:
- Header/branding sederhana yang konsisten (nama "laporan", bukan sekadar subjek email generik)
- Struktur visual jelas: ringkasan angka utama di atas (highlight), detail di bawah
- Grafik yang disesuaikan warnanya (bukan default library), konsisten dengan identitas visual laporan
- Subjek email yang informatif dan spesifik (misal: "Sales Report — Week of [tanggal]: Revenue up 12%"), bukan generik ("Automated Report")

## 7. Deliverables

- Repository GitHub publik dengan struktur jelas (`sheets/`, `processing/`, `email/`, `scheduler/`)
- README.md: masalah yang diselesaikan, arsitektur singkat, contoh screenshot email yang diterima, penjelasan keputusan teknis
- Contoh email laporan (screenshot) disertakan di README sebagai bukti visual
- Case study singkat: skenario bisnis yang disasar (UMKM/toko online kecil yang belum punya rutinitas laporan)

## 8. Tech Stack

| Layer | Tools |
|---|---|
| Sumber data | Google Sheets API (service account) |
| Pengolahan | Python, pandas |
| Visualisasi (untuk email) | matplotlib/plotly (styled, export sebagai gambar) |
| Pengiriman email | Gmail API |
| Penjadwalan | GitHub Actions (cron) |
| Credential storage | Environment variable / GitHub Secrets (service account JSON, tidak hardcoded) |
| Version control | Git + GitHub |

## 9. Kriteria Selesai (Definition of Done)

- [ ] Sistem berhasil membaca data dari Google Sheets tanpa intervensi manual
- [ ] Laporan email terkirim otomatis sesuai jadwal (minimal 1x percobaan berhasil end-to-end)
- [ ] Desain email sudah lolos review visual (lihat Bagian 6) — tidak terlihat generic
- [ ] Ada log yang mencatat status tiap run (sukses/gagal)
- [ ] README + case study lengkap, termasuk screenshot email
- [ ] Credential (service account, Gmail API token) tidak ada yang hardcoded di kode
