from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from ara_screener import data as data_mod

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
ALL_TICKERS_PATH = os.path.join(DATA_DIR, "idx_tickers.csv")
LQ45_PATH = os.path.join(DATA_DIR, "idx_lq45.csv")

BOARD_OPTIONS = ["Utama", "Pengembangan", "Pemantauan Khusus", "Akselerasi", "Ekonomi Baru"]

st.set_page_config(page_title="ARA Screener", page_icon="\U0001F4C8", layout="wide")


@st.cache_data(ttl=3600)
def _load_universe(path: str) -> pd.DataFrame:
    return data_mod.load_ticker_universe(path)


@st.cache_data(ttl=300, show_spinner=False)
def _load_summary(kodes: tuple[str, ...], universe_key: str) -> pd.DataFrame:
    universe = _load_universe(ALL_TICKERS_PATH if universe_key == "all" else LQ45_PATH)
    history = data_mod.fetch_price_history(list(kodes))
    return data_mod.build_summary(history, universe)


def _highlight_progress(val: float) -> str:
    if val >= 100:
        return "background-color: #1e7d32; color: white; font-weight: bold"
    if val >= 90:
        return "background-color: #f9a825; color: black"
    return ""


def main() -> None:
    st.title("ARA Screener \U0001F4C8")
    st.caption(
        "Screener saham yang mendekati / berpotensi Auto Reject Atas (ARA) di BEI. "
        "Data harga dari Yahoo Finance (bisa delay), bukan rekomendasi investasi."
    )

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
        score_threshold = st.slider("Ambang skor 'Potensi ARA'", min_value=0, max_value=100, value=50)

        st.divider()
        refresh = st.button("\U0001F504 Muat / Refresh data", type="primary", use_container_width=True)

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

    st.caption(f"Memantau {len(kodes)} saham.")

    if refresh:
        _load_summary.clear()

    try:
        with st.spinner(f"Mengambil data harga untuk {len(kodes)} saham..."):
            df = _load_summary(kodes, universe_key if universe_key != "custom" else "all")
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

    col1, col2, col3 = st.columns(3)
    col1.metric("Saham dipantau", len(df))
    col2.metric("Mendekati ARA", int((df["progress_ke_ara_pct"] >= proximity_threshold).sum()))
    col3.metric("Sudah kena ARA hari ini", int((df["progress_ke_ara_pct"] >= 100).sum()))

    tab1, tab2, tab3 = st.tabs(["\U0001F53A Mendekati ARA", "\U0001F52E Potensi ARA", "\U0001F4CB Semua data"])

    display_cols = {
        "kode": "Kode",
        "nama": "Nama",
        "harga_terakhir": "Harga",
        "prev_close": "Prev Close",
        "perubahan_pct": "% Chg",
        "harga_limit_ara": "Limit ARA",
        "progress_ke_ara_pct": "Progress ke ARA (%)",
        "volume_ratio": "Volume Ratio",
        "skor_potensi": "Skor Potensi",
    }

    with tab1:
        near = df[df["progress_ke_ara_pct"] >= proximity_threshold].sort_values(
            "progress_ke_ara_pct", ascending=False
        )
        st.write(f"{len(near)} saham dengan harga >= {proximity_threshold}% dari batas ARA.")
        if near.empty:
            st.info("Tidak ada saham yang memenuhi ambang ini saat ini.")
        else:
            styled = near[list(display_cols)].rename(columns=display_cols).style.map(
                _highlight_progress, subset=["Progress ke ARA (%)"]
            ).format(
                {
                    "Harga": "{:,.0f}",
                    "Prev Close": "{:,.0f}",
                    "% Chg": "{:+.2f}%",
                    "Limit ARA": "{:,.0f}",
                    "Progress ke ARA (%)": "{:.1f}%",
                    "Volume Ratio": "{:.2f}x",
                    "Skor Potensi": "{:.1f}",
                }
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

    with tab2:
        potential = df[df["skor_potensi"] >= score_threshold].sort_values(
            "skor_potensi", ascending=False
        )
        st.write(f"{len(potential)} saham dengan skor potensi >= {score_threshold}.")
        st.caption(
            "Skor gabungan dari: kedekatan ke ARA, lonjakan volume vs rata-rata 20 hari, "
            "gap up saat open, dan jumlah hari beruntun naik. Bukan prediksi pasti."
        )
        if potential.empty:
            st.info("Tidak ada saham yang memenuhi ambang skor ini saat ini.")
        else:
            styled = potential[list(display_cols)].rename(columns=display_cols).style.map(
                _highlight_progress, subset=["Progress ke ARA (%)"]
            ).format(
                {
                    "Harga": "{:,.0f}",
                    "Prev Close": "{:,.0f}",
                    "% Chg": "{:+.2f}%",
                    "Limit ARA": "{:,.0f}",
                    "Progress ke ARA (%)": "{:.1f}%",
                    "Volume Ratio": "{:.2f}x",
                    "Skor Potensi": "{:.1f}",
                }
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

    with tab3:
        search = st.text_input("Cari kode saham")
        table = df.sort_values("skor_potensi", ascending=False)
        if search:
            table = table[table["kode"].str.contains(search.upper())]
        st.dataframe(
            table[list(display_cols)].rename(columns=display_cols),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.caption(
        "⚠️ Bukan nasihat keuangan. Batas ARA dihitung dari aturan asimetris BEI "
        "(berlaku 8 Apr 2025: ARA 35%/25%/20% berdasarkan harga acuan, ARB 15%) tanpa "
        "pembulatan fraksi harga resmi, jadi bisa sedikit berbeda dari sistem perdagangan riil. "
        "Data harga: Yahoo Finance (bisa delay). Daftar emiten: "
        "[wildangunawan/Dataset-Saham-IDX](https://github.com/wildangunawan/Dataset-Saham-IDX) (CC BY-NC 4.0)."
    )


if __name__ == "__main__":
    main()
