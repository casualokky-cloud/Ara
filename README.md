# ARA Screener

Dashboard Streamlit untuk memantau saham IDX yang **mendekati** batas Auto
Reject Atas (ARA) atau punya **potensi** ke arah sana, berdasarkan data harga
dari Yahoo Finance.

⚠️ **Bukan nasihat keuangan.** Skor & indikator di sini murni heuristik dari
harga dan volume harian — bukan prediksi, dan bukan pengganti analisis
fundamental atau berita korporasi.

## Fitur

- **Mendekati ARA**: saham yang harganya sudah di atas ambang tertentu
  (misal 90%) dari batas ARA hari ini.
- **Potensi ARA**: skor 0-100 gabungan dari kedekatan ke ARA, lonjakan
  volume vs rata-rata 20 hari, gap up saat open, dan hari beruntun naik
  (lihat `ara_screener/scoring.py` untuk formula lengkap).
- Aturan ARA/ARB otomatis mengikuti tier harga acuan sesuai aturan asimetris
  BEI (berlaku sejak 8 April 2025) — lihat `ara_screener/rules.py`.
- Universe saham: LQ45 (cepat), semua saham IDX (~950, lebih lambat), atau
  upload daftar kode saham sendiri (CSV).

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan

```bash
streamlit run ara_screener/app.py
```

Buka `http://localhost:8501` di browser.

## Memperbarui daftar emiten

Daftar kode saham (`data/idx_tickers.csv`, `data/idx_lq45.csv`) berasal dari
dataset publik [wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX)
(CC BY-NC 4.0, non-komersial dengan atribusi). Untuk memperbarui:

```bash
python scripts/update_tickers.py
```

## Batasan yang perlu diketahui

- Data Yahoo Finance untuk saham IDX biasanya delay beberapa menit dan
  kadang tidak update saat market baru buka.
- Harga limit ARA/ARB dihitung dari persentase saja, **tanpa** pembulatan ke
  fraksi harga (tick size) resmi BEI — bisa berbeda beberapa rupiah dari
  sistem perdagangan riil. Jangan dipakai untuk memasang order.
- Skor "Potensi ARA" adalah heuristik sederhana berbasis aturan (rule-based),
  bukan model prediksi statistik/ML.
- Fetching seluruh ~950 saham lewat yfinance bisa memakan waktu dan rawan
  rate limit — mulai dari universe LQ45 dulu untuk pengujian cepat.
