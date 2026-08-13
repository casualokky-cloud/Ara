"""Pengambilan data harga saham IDX via yfinance dan penyusunan ringkasan screener."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

CHUNK_SIZE = 60
LOOKBACK_DAYS = 45  # cukup untuk hitung rata-rata volume 20 hari + buffer hari libur


def load_ticker_universe(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={"code": "kode", "name": "nama", "listingBoard": "papan"})
    return df[["kode", "nama", "papan"]].dropna(subset=["kode"]).reset_index(drop=True)


def yf_symbol(kode: str) -> str:
    return f"{kode.strip().upper()}.JK"


def _chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def fetch_price_history(kodes: list[str], period_days: int = LOOKBACK_DAYS) -> dict[str, pd.DataFrame]:
    """Ambil histori harga harian per kode saham (tanpa suffix .JK sebagai key).

    period_days bisa dibikin lebih panjang dari default (misal buat backtest yang
    butuh berbulan-bulan histori, bukan cuma 20-45 hari buat screening harian)."""
    result: dict[str, pd.DataFrame] = {}
    symbols = [yf_symbol(k) for k in kodes]

    for batch in _chunks(symbols, CHUNK_SIZE):
        raw = yf.download(
            tickers=batch,
            period=f"{period_days}d",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=False,
        )
        if raw is None or raw.empty:
            continue

        if len(batch) == 1:
            symbol = batch[0]
            df = raw.dropna(how="all")
            if not df.empty:
                result[symbol[:-3]] = df
            continue

        for symbol in batch:
            if symbol not in raw.columns.get_level_values(0):
                continue
            df = raw[symbol].dropna(how="all")
            if not df.empty:
                result[symbol[:-3]] = df

    return result


def build_summary(price_history: dict[str, pd.DataFrame], universe: pd.DataFrame) -> pd.DataFrame:
    from . import accumulation
    from . import rules
    from . import scoring

    rows = []
    names = dict(zip(universe["kode"], universe["nama"]))
    boards = dict(zip(universe["kode"], universe["papan"]))

    for kode, df in price_history.items():
        df = df.sort_index()
        if len(df) < 2:
            continue

        today = df.iloc[-1]
        prev_close = float(df.iloc[-2]["Close"])
        if prev_close <= 0:
            continue

        last_price = float(today["Close"])
        today_high = float(today["High"])
        today_low = float(today["Low"])
        today_open = float(today["Open"])
        volume = float(today["Volume"])

        today_range = today_high - today_low
        closing_strength_pct = (
            (last_price - today_low) / today_range * 100 if today_range > 0 else float("nan")
        )

        vol_window = df.iloc[-21:-1]["Volume"]
        avg_volume_20 = float(vol_window.mean()) if len(vol_window) > 0 else float("nan")
        volume_ratio = volume / avg_volume_20 if avg_volume_20 else float("nan")

        closes = df["Close"]
        streak = 0
        for i in range(len(closes) - 1, 0, -1):
            if closes.iloc[i] > closes.iloc[i - 1]:
                streak += 1
            else:
                break

        band = rules.get_band(prev_close)
        limit_ara = rules.ara_price(prev_close)

        change_pct = (last_price - prev_close) / prev_close
        gap_pct = (today_open - prev_close) / prev_close
        progress_to_ara = last_price / limit_ara if limit_ara else float("nan")
        high_progress_to_ara = today_high / limit_ara if limit_ara else float("nan")

        cmf_20 = accumulation.chaikin_money_flow(df)
        obv_trend_20 = accumulation.obv_trend(df)
        harga_20d_change_pct = accumulation.price_change_over(df)

        row = {
            "kode": kode,
            "nama": names.get(kode, ""),
            "papan": boards.get(kode, ""),
            "tanggal_data": df.index[-1].date(),
            "prev_close": prev_close,
            "harga_terakhir": last_price,
            "perubahan_pct": change_pct * 100,
            "batas_ara_pct": band.ara_pct * 100,
            "harga_limit_ara": limit_ara,
            "progress_ke_ara_pct": progress_to_ara * 100,
            "high_progress_ke_ara_pct": high_progress_to_ara * 100,
            "kekuatan_closing_pct": closing_strength_pct,
            "gap_pct": gap_pct * 100,
            "volume": volume,
            "avg_volume_20d": avg_volume_20,
            "volume_ratio": volume_ratio,
            "streak_naik": streak,
            "cmf_20": cmf_20,
            "obv_trend_20": obv_trend_20,
            "harga_20d_change_pct": harga_20d_change_pct,
        }
        row["skor_potensi"] = scoring.potential_score(row)
        row["skor_akumulasi_mentah"] = accumulation.accumulation_score(
            cmf_20, obv_trend_20, harga_20d_change_pct
        )
        rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty:
        # yfinance nggak update semua ticker bersamaan -- sebagian saham bisa masih nyangkut
        # di bar kemarin sementara yang lain sudah dapat bar hari ini. Kalau dibiarkan,
        # df.iloc[-1] tiap saham diam-diam merujuk ke TANGGAL YANG BEDA-BEDA, jadi tabelnya
        # kelihatan "kecampur" data kemarin & hari ini tanpa ada penanda apa pun. Tanggal
        # bar terbanyak di seluruh universe dianggap sebagai hari perdagangan acuan; saham
        # yang bar terakhirnya beda dari itu ditandai `data_terkini=False` biar bisa
        # difilter di level tampilan (lihat app.py).
        tanggal_acuan = result["tanggal_data"].mode().iloc[0]
        result["data_terkini"] = result["tanggal_data"] == tanggal_acuan

        # Saham dengan volume hari ini jauh di bawah rata-rata 20 hari dikeluarkan dari
        # ranking sama sekali — di volume setipis itu, CMF/OBV gampang disesatkan segelintir
        # transaksi kecil dan nggak merepresentasikan tekanan beli/jual yang sebenarnya
        # (lihat docstring accumulation.py, kasus MKTR).
        result["akumulasi_likuid"] = result["volume_ratio"] >= accumulation.MIN_VOLUME_RATIO
        result["skor_akumulasi"] = float("nan")
        liquid = result["akumulasi_likuid"]
        if liquid.any():
            # Skor akumulasi mentah gampang "terinflasi" bareng-bareng pas market lagi uptrend
            # (banyak saham kebagian CMF/OBV positif sekaligus), jadi ambang skor absolut jadi
            # nggak diskriminatif. Ranking persentil relatif ke saham LIKUID yang lagi dipantau
            # bikin cuma yang beneran menonjol HARI ITU yang dapat skor tinggi, apa pun kondisi
            # pasarnya secara umum.
            result.loc[liquid, "skor_akumulasi"] = (
                result.loc[liquid, "skor_akumulasi_mentah"].rank(pct=True) * 100
            )
    return result
