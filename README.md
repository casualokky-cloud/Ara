# ARA Screener

Dashboard Streamlit untuk memantau saham IDX yang **mendekati** batas Auto
Reject Atas (ARA) atau punya **potensi** ke arah sana, berdasarkan data harga
dari Yahoo Finance.

⚠️ **Bukan nasihat keuangan.** Skor & indikator di sini murni heuristik dari
harga dan volume harian — bukan prediksi, dan bukan pengganti analisis
fundamental atau berita korporasi.

## Fitur

- **Auto-refresh harian jam 08:30 WIB**: cache data screener (`_load_summary`)
  otomatis "lupa" data hari sebelumnya begitu ada yang buka dashboard setelah
  jam 08:30 WIB — nggak nunggu TTL cache lewat, nggak perlu klik Refresh
  manual, dan nggak butuh reboot app atau scheduler eksternal. Diimplementasi
  murni sebagai bagian dari cache key (`_trading_day_key()` di `app.py`), jadi
  jalan otomatis di proses Streamlit yang sama, kapan pun ada yang mengakses
  setelah jam segitu. Ubah jamnya lewat `DAILY_RESET_HOUR`/`DAILY_RESET_MINUTE`
  di `ara_screener/app.py` kalau perlu.
- **Mendekati ARA**: saham yang harganya sudah di atas ambang tertentu
  (misal 90%) dari batas ARA hari ini. Termasuk kolom "Kekuatan Closing"
  untuk menilai apakah demand-nya masih kuat di penutupan.
- **Momentum Hari Ini**: skor 0-100 gabungan dari kedekatan ke ARA, lonjakan
  volume vs rata-rata 20 hari, gap up saat open, dan hari beruntun naik
  (lihat `ara_screener/scoring.py`). Ini menandai saham yang **sedang**
  bergerak hari itu — kalau proximity-nya sudah tinggi, itu artinya harga
  SUDAH bergerak duluan, bukan sinyal untuk masuk lebih awal.
- **Akumulasi**: dari indikator teknikal Chaikin Money Flow (CMF) dan tren
  OBV, dengan bonus kalau harga belum banyak bergerak (belum breakout) —
  lihat `ara_screener/accumulation.py`. Ini kebalikan dari tab Momentum:
  mencari kandidat SEBELUM harga bergerak, bukan sesudahnya. Skornya
  ditampilkan sebagai **persentil** (0-100) relatif ke universe yang lagi
  dipantau — bukan skor absolut — supaya threshold-nya tetap diskriminatif
  walau lagi market-wide uptrend (persentil 90 = 10% paling menonjol hari
  itu, dari universe/papan pencatatan yang kamu pilih). Saham dengan Volume
  Ratio di bawah `accumulation.MIN_VOLUME_RATIO` (default 0.3x) dikeluarkan
  dari ranking ini sama sekali — di volume setipis itu CMF/OBV gampang
  disesatkan segelintir transaksi kecil (kasus nyata: MKTR sempat nangkring
  persentil 100 padahal broker summary riilnya net distribution, pas Volume
  Ratio-nya cuma 0.11x).
- **Backtest**: muter ulang histori harga dan hitung skor Akumulasi tiap hari
  seolah-olah cuma tau data sampai hari itu (nggak nyontek hasil besok), lalu
  bandingkan hit rate "kena ARA besok" dari persentil atas vs base rate acak
  — lihat `ara_screener/backtest.py`. Ngasih angka "lift" yang jelas (bukan
  vibes) buat tau skor Akumulasi beneran ada nilainya atau nggak, sekaligus
  cara buat tau apakah formulanya perlu di-tuning lagi.
- **Panduan**: tab di dashboard, isinya cara baca tiap tab/kolom &
  contoh alur pakai — hidup di kode yang sama (`ara_screener/app.py`,
  fungsi `_render_panduan`), jadi otomatis nyambung tiap kali fitur di atas
  berubah, nggak kayak dokumen terpisah yang gampang basi.
- **Kalender Event Penting**: expander di bagian atas halaman, daftar tanggal
  yang bisa gerakin IHSG — FOMC, RDG Bank Indonesia, evaluasi/rebalancing
  indeks (FTSE Russell, MSCI, LQ45/IDX30/IDX80 BEI), rilis data ekonomi
  (inflasi, PDB), sampai pidato kenegaraan. Sengaja dirender SEBELUM data
  harga di-fetch, jadi tetap muncul walau yfinance lagi error/rate-limit.
  Datanya statis & dikurasi manual di `data/kalender_penting.csv` (kolom
  `sumber` buat verifikasi) — lihat bagian "Memperbarui kalender" di bawah.
- Aturan ARA/ARB otomatis mengikuti tier harga acuan sesuai aturan asimetris
  BEI (berlaku sejak 8 April 2025) — lihat `ara_screener/rules.py`.
- Universe saham: LQ45 (cepat), semua saham IDX (~950, lebih lambat), atau
  upload daftar kode saham sendiri (CSV).

### Soal bandarmology

Skor Akumulasi di atas **bukan** bandarmology. Bandarmology asli (data
broker mana net buy/sell besar di suatu saham) butuh sumber data broker
summary yang tidak tersedia lewat yfinance — biasanya dari data historis
transaksi per-broker (IDX menyediakan lewat produk data berbayar, atau
lewat platform seperti Stockbit/RTI Business yang butuh langganan/API key
sendiri). Menambahkan ini adalah pekerjaan terpisah: butuh langganan sumber
data tersebut, lalu modul fetch & parsing baru mirip `data.py`.

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan

```bash
streamlit run ara_screener/app.py
```

Buka `http://localhost:8501` di browser.

## Email pagi otomatis (Momentum Hari Ini)

`.github/workflows/morning-momentum-email.yml` + `scripts/send_morning_momentum.py`
ngirim email berisi tab Momentum Hari Ini tiap hari kerja jam **09:05 WIB** lewat
GitHub Actions (bukan lewat dashboard, biar tetap jalan walau nggak ada yang buka
Streamlit Cloud-nya).

Setup (sekali aja):

1. Aktifkan **2-Step Verification** di akun Google pengirim (syarat App Password),
   di [myaccount.google.com/security](https://myaccount.google.com/security).
2. Bikin **App Password** di [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   (pilih app "Mail"), copy password 16 digit yang muncul.
3. Di repo GitHub ini: **Settings → Secrets and variables → Actions → New repository secret**,
   tambahin 3 secret:
   - `SMTP_USERNAME` — alamat Gmail pengirim (boleh sama dengan tujuan).
   - `SMTP_PASSWORD` — App Password 16 digit dari langkah 2 (bukan password akun biasa).
   - `EMAIL_TO` — alamat tujuan email.
4. Cek jalan apa nggak tanpa nunggu jadwal: tab **Actions** di repo → pilih workflow
   "Morning Momentum Email" → **Run workflow**.

Ambang skor (default 50) & papan pencatatan (default "Utama") bisa diubah lewat
konstanta di `scripts/send_morning_momentum.py`, atau tambahin repository variable
`MOMENTUM_THRESHOLD` di GitHub Settings buat ganti ambang tanpa edit kode.

⚠️ Data ~5 menit setelah open itu volume & momentumnya masih tipis banget — ARA
kolomnya kemungkinan besar masih kosong pagi-pagi, isinya lebih ke gap-up & streak
dari hari sebelumnya. Jadwal GitHub Actions juga kadang meleset beberapa menit dari
jam yang di-set (bukan real-time cron), dan workflow terjadwal otomatis nonaktif
kalau repo nggak ada commit sama sekali selama 60 hari.

## Memperbarui kalender event penting

`data/kalender_penting.csv` (kolom: `tanggal_mulai, tanggal_selesai, event,
kategori, catatan, sumber`) dikurasi manual, bukan dari API kalender ekonomi
live. Beberapa baris (rilis inflasi BPS, review FTSE September) bertanda
"perkiraan" di kolom `catatan` karena tanggal pastinya belum diumumkan resmi
saat data ini disusun (~Agustus 2026). Perlu di-update berkala:

- Jadwal FOMC: [federalreserve.gov](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
- Jadwal RDG Bank Indonesia: [bi.go.id](https://www.bi.go.id)
- Review FTSE Russell Indonesia: [research.ftserussell.com](https://research.ftserussell.com/products/index-notices/home)
- Review MSCI: [msci.com/indexes/quarterly-index-review](https://www.msci.com/indexes/quarterly-index-review)
- Evaluasi mayor indeks BEI (LQ45/IDX30/IDX80): pengumuman resmi di [idx.co.id](https://www.idx.co.id)
- Rilis data ekonomi (inflasi, PDB): [bps.go.id/id/pressrelease](https://www.bps.go.id/id/pressrelease)

Tinggal edit CSV-nya langsung (baris baru = event baru), commit & push — tab
Kalender di dashboard otomatis kebaca ulang.

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
- Skor "Momentum Hari Ini" dan "Akumulasi" adalah heuristik sederhana
  berbasis aturan (rule-based) dari harga & volume historis, **belum**
  divalidasi/backtest terhadap histori ARA riil, dan bukan model prediksi
  statistik/ML.
- Fetching seluruh ~950 saham lewat yfinance bisa memakan waktu dan rawan
  rate limit — mulai dari universe LQ45 dulu untuk pengujian cepat.
