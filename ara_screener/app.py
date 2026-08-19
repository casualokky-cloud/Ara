from __future__ import annotations

import datetime as dt
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from ara_screener import accumulation, backtest, data as data_mod

DATA_DIR = os.path.join(_REPO_ROOT, "data")
ALL_TICKERS_PATH = os.path.join(DATA_DIR, "idx_tickers.csv")
LQ45_PATH = os.path.join(DATA_DIR, "idx_lq45.csv")
KALENDER_PATH = os.path.join(DATA_DIR, "kalender_penting.csv")

BOARD_OPTIONS = ["Utama", "Pengembangan", "Pemantauan Khusus", "Akselerasi", "Ekonomi Baru"]

WIB = dt.timezone(dt.timedelta(hours=7))
DAILY_RESET_HOUR, DAILY_RESET_MINUTE = 8, 30  # jam mulai "hari baru" buat cache screener
AUTOREFRESH_INTERVAL_MS = 5 * 60 * 1000  # cek tiap 5 menit -- selaras sama TTL _load_summary


def _trading_day_key(now: dt.datetime | None = None) -> str:
    """Tanggal efektif yang cuma maju sekali per hari, tepat jam 08:30 WIB.

    Dipakai sebagai bagian dari cache key `_load_summary` biar tab-tab screener otomatis
    fetch ulang dari nol begitu ada yang buka dashboard setelah jam segitu -- bukan nunggu
    TTL cache lewat, dan nggak butuh reboot app atau scheduler eksternal. Sebelum jam
    08:30, masih dianggap "hari kemarin" (cache lama, kalau masih ada, tetap kepakai)."""
    now = now or dt.datetime.now(WIB)
    cutoff = now.replace(hour=DAILY_RESET_HOUR, minute=DAILY_RESET_MINUTE, second=0, microsecond=0)
    effective_date = now.date() if now >= cutoff else (now - dt.timedelta(days=1)).date()
    return effective_date.isoformat()

# Streamlit's st.cache_data hashes _load_summary's OWN source code + args, not the code of
# data_mod.build_summary/accumulation.py that it calls internally. So editing those modules
# without touching this function's body leaves stale cached DataFrames (missing/renamed
# columns from before the edit) being served after a redeploy, even a full reboot, until the
# TTL expires. Bump this whenever build_summary's output columns change, so it's part of the
# cache key and old entries can never match.
SCHEMA_VERSION = "5"

st.set_page_config(page_title="ARA Screener", page_icon="\U0001F4C8", layout="wide")


@st.cache_data(ttl=3600)
def _load_universe(path: str) -> pd.DataFrame:
    return data_mod.load_ticker_universe(path)


@st.cache_data(ttl=3600)
def _load_kalender(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["tanggal_mulai", "tanggal_selesai"])
    return df.sort_values("tanggal_mulai").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def _load_summary(
    kodes: tuple[str, ...], universe_key: str, schema_version: str, trading_day: str
) -> pd.DataFrame:
    universe = _load_universe(ALL_TICKERS_PATH if universe_key == "all" else LQ45_PATH)
    history = data_mod.fetch_price_history(list(kodes))
    return data_mod.build_summary(history, universe)


@st.cache_data(ttl=3600, show_spinner=False)
def _run_backtest(kodes: tuple[str, ...], lookback_days: int, schema_version: str) -> pd.DataFrame:
    history = data_mod.fetch_price_history(list(kodes), period_days=lookback_days)
    return backtest.run_backtest(history)


def _highlight_progress(val: float) -> str:
    if val >= 100:
        return "background-color: #1e7d32; color: white; font-weight: bold"
    if val >= 90:
        return "background-color: #f9a825; color: black"
    return ""


def _render_panduan() -> None:
    """Panduan pakai dashboard, hidup di kode yang sama jadi otomatis ikut ter-update
    tiap kali tab/kolom/skor di atas berubah — nggak ada dokumen terpisah yang basi."""
    st.markdown(
        "Panduan cara baca dashboard ini. Karena hidup satu kode sama dashboard-nya, isinya "
        "otomatis nyambung tiap kali ada perubahan fitur."
    )

    with st.expander("Apa itu ARA Screener?", expanded=True):
        st.markdown(
            "Dashboard ini mindai saham-saham di Bursa Efek Indonesia (BEI/IDX) buat nemuin "
            "saham yang **mendekati atau berpotensi kena Auto Reject Atas (ARA)** — batas "
            "kenaikan harga maksimal dalam satu hari perdagangan. Ini bukan alat prediksi — "
            "anggap sebagai **alat bantu nyaring** dari ratusan saham jadi daftar pendek yang "
            "layak diperhatikan lebih lanjut.\n\n"
            "| Tab | Buat apa |\n"
            "|---|---|\n"
            "| 🔺 Mendekati ARA | Saham yang harganya SUDAH deket/kena batas ARA hari ini. |\n"
            "| 🔥 Momentum Hari Ini | Saham yang lagi 'panas' hari ini (skor gabungan). |\n"
            "| 🌱 Akumulasi | Saham yang mungkin lagi 'dikumpulin' diam-diam, SEBELUM harga bergerak. |\n"
            "| 📋 Semua data | Semua saham yang dipantau, bisa di-search. |\n"
            "| 🧪 Backtest | Uji beneran: apakah skor Akumulasi tinggi historisnya lebih sering diikuti ARA besoknya, dibanding pilih saham random? |\n\n"
            "Di luar tab-tab itu, ada juga expander **🗓️ Kalender Event Penting** di bagian atas "
            "halaman (di atas sini) — daftar tanggal yang bisa gerakin IHSG: FOMC, RDG BI, "
            "rebalancing indeks (FTSE/MSCI/BEI), rilis data ekonomi, sampai pidato kenegaraan."
        )

    with st.expander("Pengaturan di sidebar"):
        st.markdown(
            "| Pengaturan | Fungsinya |\n"
            "|---|---|\n"
            "| Universe saham | LQ45 (cepat) / Semua saham IDX (~950, lebih lambat) / Upload CSV kode saham sendiri. |\n"
            "| Papan pencatatan | Filter berdasarkan papan: Utama, Pengembangan, Pemantauan Khusus, dll. |\n"
            "| Ambang 'Mendekati ARA' | Batas minimal progress ke ARA buat masuk tab 1. |\n"
            "| Ambang skor 'Momentum Hari Ini' | Batas minimal skor buat masuk tab 2. |\n"
            "| Ambang persentil 'Akumulasi' | Mis. 80 = tampilin cuma 20% saham paling menonjol. |\n"
            "| Muat / Refresh data | Ambil data harga terbaru & buang cache lama, kapan aja. |\n"
            "| Bersihkan data kemarin | Sama-sama buang cache lama & ambil ulang dari nol; "
            "tombol terpisah biar niatnya jelas kalau cuma mau mastiin tabel bukan sisa hari kemarin. |\n\n"
            f"Selain itu, data screener otomatis full-refresh sendiri tiap hari jam "
            f"**{DAILY_RESET_HOUR:02d}:{DAILY_RESET_MINUTE:02d} WIB** — begitu ada yang buka "
            "dashboard setelah jam segitu, data kemarin otomatis dibuang dan diambil ulang "
            "dari nol, nggak perlu diklik manual. Halaman ini juga reload sendiri tiap "
            f"{AUTOREFRESH_INTERVAL_MS // 60000} menit SELAMA tab-nya kebuka di browser, "
            "jadi nggak perlu nunggu kamu buka/reload manual buat nge-trigger refresh jam "
            "08:30-nya — tapi ini cuma jalan kalau tab-nya beneran kebuka, bukan proses "
            "background yang jalan sendiri walau browser ditutup.\n\n"
            "Tips: pertama kali coba, pakai universe **LQ45** dulu biar cepat, baru pindah ke "
            "'Semua saham IDX' kalau mau eksplor lebih luas."
        )

    with st.expander("Cara baca tab Mendekati ARA & Momentum Hari Ini"):
        st.markdown(
            "| Kolom | Artinya |\n"
            "|---|---|\n"
            "| Harga / Prev Close / % Chg | Harga sekarang, penutupan kemarin, dan perubahannya. |\n"
            "| Limit ARA | Harga batas ARA hari ini (Prev Close x (1 + persentase ARA)). |\n"
            "| Progress ke ARA (%) | Seberapa dekat harga sekarang ke Limit ARA. 100% = sudah kena ARA. |\n"
            "| Kekuatan Closing (%) | Posisi harga sekarang dalam range high-low hari ini — makin tinggi, makin dekat ke high (demand masih kuat). |\n"
            "| Volume Ratio | Volume hari ini dibanding rata-rata 20 hari. |\n"
            "| Skor Momentum | Gabungan proximity ke ARA (35 poin), lonjakan volume (30 poin), gap up (20 poin), dan hari beruntun naik (15 poin). |\n\n"
            "⚠️ **Penting:** skor/progress tinggi = saham LAGI panas HARI INI, bukan prediksi "
            "bakal ARA. Kalau kamu beli yang paling atas skornya, kemungkinan besar kamu beli "
            "di titik dia udah paling deket top hari itu — telat masuk. Buat kandidat SEBELUM "
            "harga bergerak, cek tab Akumulasi."
        )

    with st.expander("Cara baca tab Akumulasi"):
        st.markdown(
            "Kebalikan dari tab Momentum: nyari saham yang mungkin lagi 'dikumpulin' diam-diam "
            "**sebelum** harga bergerak.\n\n"
            "| Kolom | Artinya |\n"
            "|---|---|\n"
            "| Chg 20D (%) | Perubahan harga 20 hari terakhir. Idealnya kecil/flat (belum breakout). |\n"
            "| CMF (20D) | Chaikin Money Flow: tekanan beli (+) / jual (-) dari posisi closing dalam range high-low, dibobot volume. |\n"
            "| Tren OBV | Apakah volume 20 hari terakhir condong ke hari naik atau turun. |\n"
            "| Persentil Akumulasi | Ranking 0-100 RELATIF ke saham lain yang dipantau hari itu, bukan skor mutlak — 90 berarti termasuk 10% paling menonjol. |\n\n"
            f"Saham dengan Volume Ratio di bawah **{accumulation.MIN_VOLUME_RATIO}x** dikeluarkan "
            "dari ranking ini sama sekali — di volume setipis itu, CMF/OBV gampang disesatkan "
            "segelintir transaksi kecil (kasus nyata pernah kejadian: sebuah saham nangkring "
            "persentil 100 padahal broker summary riil di Stockbit nunjukin *Big Distribution*, "
            "pas Volume Ratio-nya cuma 0.11x).\n\n"
            "🚫 **INI BUKAN bandarmology** (data broker net-buy beneran) — murni dari harga & "
            "volume historis, jadi tetap bisa salah/false positive. Anggap sebagai watchlist "
            "awal, bukan sinyal beli."
        )

    with st.expander("Cara pakai buat 2 gaya trading"):
        st.markdown(
            "**Beli pagi, jual sore (chasing momentum intraday):**\n"
            "1. Buka tab Akumulasi, cari kandidat persentil tinggi tapi Chg 20D masih kecil (belum breakout) — watchlist awal.\n"
            "2. Pantau sepanjang hari: kalau kandidat mulai masuk tab Mendekati ARA dengan progress di kisaran 50-80% (bukan yang udah 95%+), itu momen lebih masuk akal buat entry.\n"
            "3. Cross-check Volume Ratio & Kekuatan Closing sebelum eksekusi — data yfinance bisa delay, tetap cek order book asli di aplikasi sekuritas.\n\n"
            "**Beli sore, jual pagi (nebak gap-up/lanjutan ARA):**\n"
            "1. Buka tab Mendekati ARA menjelang penutupan, filter progress sudah ≥100%.\n"
            "2. Cek Kekuatan Closing — yang closing-nya kuat berarti demand masih tebal sampai bel penutupan, indikasi kasar sisa antrian beli yang belum kesalur.\n"
            "3. Ingat: dashboard ini nggak punya data antrian beli (order book depth) beneran — ini cuma proxy kasar, bukan kepastian."
        )

    with st.expander("Cara baca tab Backtest"):
        st.markdown(
            "Ngukur beneran apakah skor Akumulasi ada nilainya, pakai data historis:\n"
            "1. Atur lookback (berapa hari histori) & ambang persentil yang mau diuji.\n"
            "2. Klik **Jalankan Backtest** — dashboard bakal muter ulang tiap hari di histori "
            "itu, hitung skor Akumulasi seolah-olah cuma tau data sampai hari itu (nggak "
            "nyontek hasil besok), lalu cek beneran apakah saham itu kena ARA besoknya.\n"
            "3. Bandingkan **Hit rate top persentil** (peluang kena ARA besok kalau ambil "
            "saham dari persentil tinggi) vs **Base rate** (peluang kalau pilih saham random). "
            "**Lift** di atas 1x berarti skornya beneran ada nilai tambah dibanding tebak-tebakan; "
            "di sekitar 1x berarti skornya nggak lebih baik dari pilih acak.\n\n"
            "Perhatikan jumlah observasi di persentil yang diuji — kalau kecil (di bawah ~30), "
            "angka hit rate/lift-nya belum tentu stabil, jangan buru-buru disimpulkan."
        )

    with st.expander("Batasan yang wajib diingat"):
        st.markdown(
            "- Data harga dari Yahoo Finance biasanya delay beberapa menit, dan nggak semua "
            "saham ke-update bersamaan — dashboard otomatis nyembunyiin saham yang bar "
            "terakhirnya masih 'nyangkut' di tanggal berbeda dari mayoritas (lihat caption "
            "'Data harga per ...' di atas tab-tab), biar nggak kecampur data kemarin & hari ini.\n"
            "- Harga Limit ARA dihitung dari persentase doang, TANPA pembulatan ke fraksi harga "
            "(tick size) resmi BEI — jangan dipakai buat pasang order.\n"
            "- Semua skor (Momentum & Akumulasi) adalah heuristik rule-based dari harga/volume "
            "historis — BELUM divalidasi/backtest terhadap histori ARA riil.\n"
            "- Tab Akumulasi BUKAN bandarmology.\n"
            "- Fetching 'Semua saham IDX' (~950 saham) bisa makan waktu beberapa menit.\n\n"
            "**Bukan nasihat keuangan.** Dashboard ini alat bantu screening, bukan rekomendasi "
            "beli/jual."
        )


_BULAN_ID = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
}


def _format_date_range(row: pd.Series) -> str:
    start, end = row["tanggal_mulai"], row["tanggal_selesai"]
    if start.date() == end.date():
        return f"{start.day} {_BULAN_ID[start.month]} {start.year}"
    if (start.month, start.year) == (end.month, end.year):
        return f"{start.day}-{end.day} {_BULAN_ID[start.month]} {start.year}"
    return f"{start.day} {_BULAN_ID[start.month]} - {end.day} {_BULAN_ID[end.month]} {end.year}"


def _render_kalender() -> None:
    """Kalender event yang bisa gerakin IHSG: FOMC, RDG BI, index rebalancing (FTSE/MSCI/BEI),
    rilis data ekonomi, sampai pidato kenegaraan. Data statis di data/kalender_penting.csv,
    dikurasi manual & perlu diperbarui berkala -- lihat kolom Sumber buat verifikasi."""
    st.caption(
        "Tanggal-tanggal yang berpotensi menggerakkan IHSG: keputusan suku bunga (The Fed & "
        "BI), evaluasi/rebalancing indeks (FTSE, MSCI, BEI), rilis data ekonomi, dan pidato "
        "kenegaraan. Data dikurasi manual, sebagian bertanda 'perkiraan' — selalu cek kolom "
        "Sumber buat verifikasi sebelum dipakai."
    )

    df = _load_kalender(KALENDER_PATH).copy()
    today = pd.Timestamp.now().normalize()
    df["hari_lagi"] = (df["tanggal_mulai"] - today).dt.days
    df["berlangsung"] = (df["tanggal_mulai"] <= today) & (today <= df["tanggal_selesai"])
    df["sudah_lewat"] = df["tanggal_selesai"] < today

    col1, col2 = st.columns([1, 2])
    hide_past = col1.checkbox("Sembunyikan yang sudah lewat", value=True, key="kalender_hide_past")
    kategori_opsi = sorted(df["kategori"].unique().tolist())
    kategori_filter = col2.multiselect(
        "Filter kategori", kategori_opsi, default=kategori_opsi, key="kalender_kategori"
    )

    view = df[df["kategori"].isin(kategori_filter)]
    if hide_past:
        view = view[~view["sudah_lewat"]]
    view = view.sort_values("tanggal_mulai")

    if view.empty:
        st.info("Nggak ada event yang cocok dengan filter ini.")
        return

    view = view.copy()
    view["Tanggal"] = view.apply(_format_date_range, axis=1)
    display_cols = {
        "Tanggal": "Tanggal",
        "event": "Event",
        "kategori": "Kategori",
        "catatan": "Catatan",
        "sumber": "Sumber",
    }
    display_df = view[list(display_cols)].rename(columns=display_cols)
    is_live = view["berlangsung"]
    is_soon = (~is_live) & view["hari_lagi"].between(0, 7)

    def _row_style(row: pd.Series) -> list[str]:
        idx = row.name
        if is_live.loc[idx]:
            return ["background-color: #7f1d1d; color: white"] * len(row)
        if is_soon.loc[idx]:
            return ["background-color: #78350f; color: white"] * len(row)
        return [""] * len(row)

    st.caption("🟥 lagi berlangsung &nbsp;&nbsp; 🟧 ≤7 hari lagi")
    st.dataframe(
        display_df.style.apply(_row_style, axis=1),
        width='stretch',
        hide_index=True,
        column_config={
            "Sumber": st.column_config.LinkColumn("Sumber", display_text="🔗"),
        },
    )


def main() -> None:
    # Reload otomatis tiap AUTOREFRESH_INTERVAL_MS selama tab dashboard terbuka, jadi begitu
    # jam lewat 08:30 WIB, halaman rerun sendiri (tanpa perlu diklik/reload manual) dan
    # otomatis dapat _trading_day_key() yang baru -> data screener full-refresh dari nol.
    # Kalau tab-nya beneran ditutup, ini nggak jalan sama sekali (JS-nya cuma hidup selama
    # halamannya kebuka di browser) -- bukan pengganti buat proses yang jalan tanpa browser.
    st_autorefresh(interval=AUTOREFRESH_INTERVAL_MS, key="daily_reset_autorefresh")

    st.title("ARA Screener \U0001F4C8")
    st.caption(
        "Screener saham yang mendekati / berpotensi Auto Reject Atas (ARA) di BEI. "
        "Data harga dari Yahoo Finance (bisa delay), bukan rekomendasi investasi."
    )

    with st.expander("\U0001F5D3️ Kalender Event Penting (bisa gerakin IHSG)"):
        _render_kalender()

    with st.sidebar:
        st.header("Pengaturan")

        universe_choice = st.radio(
            "Universe saham",
            options=["LQ45 (cepat)", "Semua saham IDX (~950, lebih lambat)", "Upload CSV sendiri"],
            index=0,
        )

        uploaded_df = None
        if universe_choice == "Upload CSV sendiri":
            upload = st.file_uploader(
                "CSV dengan kolom 'kode' (boleh tambahan 'nama', 'papan')", type="csv"
            )
            if upload is not None:
                uploaded_df = pd.read_csv(upload)
                if "kode" not in uploaded_df.columns:
                    st.error("CSV harus punya kolom 'kode'.")
                    uploaded_df = None

        board_filter = st.multiselect("Papan pencatatan", BOARD_OPTIONS, default=["Utama"])

        st.divider()
        proximity_threshold = st.slider(
            "Ambang 'Mendekati ARA' (% dari batas ARA)", min_value=50, max_value=100, value=90
        )
        score_threshold = st.slider("Ambang skor 'Momentum Hari Ini'", min_value=0, max_value=100, value=50)
        akumulasi_threshold = st.slider(
            "Ambang persentil 'Akumulasi' (mis. 80 = top 20%)", min_value=0, max_value=100, value=80
        )

        st.divider()
        refresh_col, cleanse_col = st.columns(2)
        with refresh_col:
            refresh = st.button("\U0001F504 Muat / Refresh data", type="primary", width='stretch')
        with cleanse_col:
            cleanse = st.button(
                "\U0001F9F9 Bersihkan data kemarin",
                width='stretch',
                help="Buang cache lama & ambil ulang data hari ini dari nol.",
            )

    if universe_choice == "Upload CSV sendiri":
        if uploaded_df is None:
            st.info("Upload file CSV di sidebar untuk mulai screening.")
            return
        universe = uploaded_df.copy()
        if "nama" not in universe.columns:
            universe["nama"] = ""
        if "papan" not in universe.columns:
            universe["papan"] = ""
        kodes = tuple(sorted(universe["kode"].dropna().unique().tolist()))
        universe_key = "custom"
    else:
        universe_key = "lq45" if universe_choice.startswith("LQ45") else "all"
        universe = _load_universe(ALL_TICKERS_PATH if universe_key == "all" else LQ45_PATH)
        if board_filter:
            universe = universe[universe["papan"].isin(board_filter)]
        kodes = tuple(sorted(universe["kode"].dropna().unique().tolist()))

    if not kodes:
        st.warning("Tidak ada saham yang cocok dengan filter papan pencatatan.")
        return

    st.caption(
        f"Memantau {len(kodes)} saham. Data efektif hari {_trading_day_key()} — otomatis "
        "full-refresh tiap hari jam 08:30 WIB (bukan cuma nunggu cache lama expired)."
    )

    if refresh or cleanse:
        _load_summary.clear()
        if cleanse:
            st.toast("Tabel dibersihkan dari data kemarin — mengambil ulang dari nol.", icon="\U0001F9F9")

    try:
        with st.spinner(f"Mengambil data harga untuk {len(kodes)} saham..."):
            df = _load_summary(
                kodes,
                universe_key if universe_key != "custom" else "all",
                SCHEMA_VERSION,
                _trading_day_key(),
            )
            if universe_key == "custom":
                df = df[df["kode"].isin(kodes)]
    except Exception as exc:  # noqa: BLE001
        st.error(
            "Gagal mengambil data harga dari Yahoo Finance. Cek koneksi internet, "
            f"atau coba lagi beberapa saat lagi.\n\nDetail error: {exc}"
        )
        return

    if df.empty:
        st.warning("Tidak ada data harga yang berhasil diambil untuk universe ini.")
        return

    n_stale = int((~df["data_terkini"]).sum())
    tanggal_acuan = df.loc[df["data_terkini"], "tanggal_data"].iloc[0] if (df["data_terkini"]).any() else None
    df = df[df["data_terkini"]].copy()

    if df.empty:
        st.warning(
            "Semua data yang berhasil diambil ternyata bukan dari hari perdagangan yang sama "
            "(kemungkinan Yahoo Finance belum update). Coba refresh lagi beberapa saat lagi."
        )
        return

    if tanggal_acuan is not None:
        st.caption(f"📅 Data harga per **{tanggal_acuan.strftime('%d %b %Y')}**.")
    if n_stale:
        st.caption(
            f"⚠️ {n_stale} saham disembunyikan dari semua tab karena data terakhirnya BUKAN dari "
            f"tanggal di atas (kemungkinan Yahoo Finance belum update saham itu) — dulu ini malah "
            "ikut ditampilkan seolah-olah data hari ini, bikin tabel kelihatan 'kecampur'."
        )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saham dipantau", len(df))
    col2.metric("Mendekati ARA", int((df["progress_ke_ara_pct"] >= proximity_threshold).sum()))
    col3.metric("Sudah kena ARA hari ini", int((df["progress_ke_ara_pct"] >= 100).sum()))
    col4.metric("Kandidat akumulasi", int((df["skor_akumulasi"] >= akumulasi_threshold).sum()))

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "\U0001F53A Mendekati ARA",
            "\U0001F525 Momentum Hari Ini",
            "\U0001F331 Akumulasi",
            "\U0001F4CB Semua data",
            "\U0001F9EA Backtest",
            "\U0001F4D6 Panduan",
        ]
    )

    momentum_cols = {
        "kode": "Kode",
        "nama": "Nama",
        "harga_terakhir": "Harga",
        "prev_close": "Prev Close",
        "perubahan_pct": "% Chg",
        "harga_limit_ara": "Limit ARA",
        "progress_ke_ara_pct": "Progress ke ARA (%)",
        "kekuatan_closing_pct": "Kekuatan Closing (%)",
        "volume_ratio": "Volume Ratio",
        "skor_potensi": "Skor Momentum",
    }
    akumulasi_cols = {
        "kode": "Kode",
        "nama": "Nama",
        "harga_terakhir": "Harga",
        "harga_20d_change_pct": "Chg 20D (%)",
        "cmf_20": "CMF (20D)",
        "obv_trend_20": "Tren OBV (hari volume)",
        "volume_ratio": "Volume Ratio",
        "skor_akumulasi": "Persentil Akumulasi",
    }

    def _momentum_table(sub_df: pd.DataFrame):
        return (
            sub_df[list(momentum_cols)]
            .rename(columns=momentum_cols)
            .style.map(_highlight_progress, subset=["Progress ke ARA (%)"])
            .format(
                {
                    "Harga": "{:,.0f}",
                    "Prev Close": "{:,.0f}",
                    "% Chg": "{:+.2f}%",
                    "Limit ARA": "{:,.0f}",
                    "Progress ke ARA (%)": "{:.1f}%",
                    "Kekuatan Closing (%)": "{:.0f}%",
                    "Volume Ratio": "{:.2f}x",
                    "Skor Momentum": "{:.1f}",
                }
            )
        )

    with tab1:
        near = df[df["progress_ke_ara_pct"] >= proximity_threshold].sort_values(
            "progress_ke_ara_pct", ascending=False
        )
        st.write(f"{len(near)} saham dengan harga >= {proximity_threshold}% dari batas ARA.")
        st.caption(
            "⚠️ Saham di sini SUDAH bergerak dekat/kena ARA hari ini — bukan sinyal buat masuk "
            "duluan. 'Kekuatan Closing' (harga terakhir relatif ke range high-low hari ini) bisa "
            "bantu menilai apakah demand-nya masih kuat sampai penutupan (relevan untuk tesis "
            "'beli sore, jual pagi') atau cuma sempat nyentuh lalu rontok."
        )
        if near.empty:
            st.info("Tidak ada saham yang memenuhi ambang ini saat ini.")
        else:
            st.dataframe(_momentum_table(near), width='stretch', hide_index=True)

    with tab2:
        potential = df[df["skor_potensi"] >= score_threshold].sort_values(
            "skor_potensi", ascending=False
        )
        st.write(f"{len(potential)} saham dengan skor momentum >= {score_threshold}.")
        st.caption(
            "Skor gabungan dari: kedekatan ke ARA, lonjakan volume vs rata-rata 20 hari, "
            "gap up saat open, dan jumlah hari beruntun naik — menandai saham yang LAGI panas "
            "HARI INI, bukan prediksi saham yang akan ARA. Buat cari kandidat SEBELUM harga "
            "bergerak, cek tab Akumulasi."
        )
        if potential.empty:
            st.info("Tidak ada saham yang memenuhi ambang skor ini saat ini.")
        else:
            st.dataframe(_momentum_table(potential), width='stretch', hide_index=True)

    with tab3:
        n_illiquid = int((~df["akumulasi_likuid"]).sum())
        n_liquid = int(df["akumulasi_likuid"].sum())
        akumulasi = df[df["skor_akumulasi"] >= akumulasi_threshold].sort_values(
            "skor_akumulasi", ascending=False
        )
        st.write(
            f"{len(akumulasi)} saham masuk persentil atas {100 - akumulasi_threshold}% "
            f"(dari {n_liquid} saham likuid yang dipantau)."
        )
        st.caption(
            "Skor dari indikator teknikal Chaikin Money Flow (tekanan beli/jual 20 hari) dan tren "
            "OBV, dengan bonus kalau harga belum banyak bergerak (belum breakout) — lalu "
            "**diurutkan sebagai persentil** relatif ke saham lain yang lagi dipantau saat ini, "
            "bukan skor absolut. Ini supaya nggak semua saham 'lolos' bareng-bareng pas market "
            "lagi hijau semua; persentil 90 berarti termasuk 10% paling menonjol hari itu. "
            "Menandai saham yang mungkin lagi 'dikumpulin' diam-diam — kandidat early-entry, "
            "kebalikan dari tab Mendekati ARA. INI BUKAN bandarmology (data broker net buy); murni "
            "dari harga & volume historis, jadi tetap bisa salah/false positive, dan hasilnya "
            "berubah tergantung universe/papan pencatatan yang kamu pilih."
        )
        if n_illiquid:
            st.caption(
                f"⚠️ {n_illiquid} saham dikeluarkan dari ranking ini karena Volume Ratio-nya "
                f"< {accumulation.MIN_VOLUME_RATIO}x (volume hari ini terlalu tipis buat sinyal "
                "CMF/OBV dipercaya — rawan false positive, cek tab Semua data kalau tetap mau "
                "lihat angkanya)."
            )
        if akumulasi.empty:
            st.info("Tidak ada saham yang memenuhi ambang persentil ini saat ini.")
        else:
            styled = (
                akumulasi[list(akumulasi_cols)]
                .rename(columns=akumulasi_cols)
                .style.format(
                    {
                        "Harga": "{:,.0f}",
                        "Chg 20D (%)": "{:+.1f}%",
                        "CMF (20D)": "{:+.2f}",
                        "Tren OBV (hari volume)": "{:+.1f}",
                        "Volume Ratio": "{:.2f}x",
                        "Persentil Akumulasi": "{:.0f}",
                    }
                )
            )
            st.dataframe(styled, width='stretch', hide_index=True)

    with tab4:
        search = st.text_input("Cari kode saham")
        table = df.sort_values("skor_potensi", ascending=False)
        if search:
            table = table[table["kode"].str.contains(search.upper())]
        all_cols = {**momentum_cols, **{k: v for k, v in akumulasi_cols.items() if k not in momentum_cols}}
        st.dataframe(
            table[list(all_cols)].rename(columns=all_cols),
            width='stretch',
            hide_index=True,
        )

    with tab5:
        st.write(
            "Muter ulang histori harga: tiap hari, hitung skor Akumulasi SEOLAH-OLAH cuma tau "
            "data sampai hari itu, lalu cek beneran apakah saham itu kena ARA di hari "
            "berikutnya. Hasilnya dibandingkan ke base rate acak dari seluruh universe, biar "
            "ketauan skor ini beneran ada 'lift'-nya atau nggak."
        )
        st.caption(
            "⚠️ Bukan jaminan strategi profitable — backtest ini nggak masukin biaya transaksi, "
            "likuiditas eksekusi riil, atau survivorship bias (saham yang sudah delisting nggak "
            "ikut kehitung). Hasil masa lalu juga nggak menjamin masa depan."
        )

        bt_col1, bt_col2 = st.columns(2)
        lookback_days = bt_col1.slider(
            "Lookback histori (hari kalender)", min_value=90, max_value=250, value=150, step=10
        )
        bt_persentil = bt_col2.slider(
            "Ambang persentil yang diuji", min_value=50, max_value=100, value=80, step=5
        )

        run_backtest_clicked = st.button("\U0001F9EA Jalankan Backtest", type="primary")
        if run_backtest_clicked:
            st.session_state["backtest_kodes"] = kodes
            st.session_state["backtest_lookback"] = lookback_days
            try:
                with st.spinner(
                    f"Mengunduh {lookback_days} hari histori untuk {len(kodes)} saham dan "
                    "menghitung ulang skor tiap hari — bisa makan waktu beberapa menit untuk "
                    "universe besar..."
                ):
                    st.session_state["backtest_result"] = _run_backtest(
                        kodes, lookback_days, SCHEMA_VERSION
                    )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Backtest gagal jalan. Detail error: {exc}")
                st.session_state.pop("backtest_result", None)

        bt_result = st.session_state.get("backtest_result")
        if bt_result is None:
            st.info("Klik 'Jalankan Backtest' buat mulai. Belum ada hasil yang disimpan.")
        elif bt_result.empty:
            st.warning("Nggak ada data yang cukup buat backtest dari universe/lookback ini.")
        else:
            summary = backtest.summarize(bt_result, persentil_threshold=bt_persentil)
            st.caption(
                f"Backtest dari {st.session_state.get('backtest_lookback', lookback_days)} hari "
                f"histori, {summary['n_saham']} saham, {summary['n_hari']} hari observasi "
                f"({summary['n_observasi']} baris total)."
            )
            m1, m2, m3 = st.columns(3)
            m1.metric(
                f"Hit rate top persentil ≥{bt_persentil}",
                f"{summary['top_rate_pct']:.1f}%",
                help=f"{summary['n_top_hit']} dari {summary['n_top']} observasi di persentil ini kena ARA besoknya.",
            )
            m2.metric(
                "Base rate (semua saham/hari)",
                f"{summary['base_rate_pct']:.1f}%",
                help="Peluang kena ARA besok kalau pilih saham random dari seluruh observasi.",
            )
            lift = summary["lift"]
            m3.metric(
                "Lift",
                f"{lift:.1f}x" if pd.notna(lift) else "n/a",
                help="Hit rate top persentil dibagi base rate. >1x berarti skornya ada nilai tambah dibanding pilih random.",
            )
            if summary["n_top"] < 30:
                st.caption(
                    f"⚠️ Cuma {summary['n_top']} observasi di atas ambang persentil ini — "
                    "sampelnya kecil, angka hit rate/lift di atas belum tentu stabil. Coba "
                    "perpanjang lookback atau perbesar universe."
                )

    with tab6:
        _render_panduan()

    st.divider()
    st.caption(
        "⚠️ Bukan nasihat keuangan. Batas ARA dihitung dari aturan asimetris BEI "
        "(berlaku 8 Apr 2025: ARA 35%/25%/20% berdasarkan harga acuan, ARB 15%) tanpa "
        "pembulatan fraksi harga resmi, jadi bisa sedikit berbeda dari sistem perdagangan riil. "
        "Skor Momentum & Akumulasi murni heuristik rule-based dari data harga/volume — belum "
        "divalidasi/backtest terhadap histori ARA riil, dan Akumulasi bukan data bandarmology "
        "(broker net buy). Data harga: Yahoo Finance (bisa delay). Daftar emiten: "
        "[wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) (CC BY-NC 4.0)."
    )


if __name__ == "__main__":
    main()
