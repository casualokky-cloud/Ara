"""
Backtest: apakah skor Akumulasi beneran punya "lift" buat nebak ARA besok?

Muter ulang histori harga per saham, hitung skor Akumulasi tiap hari SEOLAH-OLAH
cuma tau data sampai hari itu (nggak nyontek hasil besok), lalu cek beneran:
apakah saham itu kena ARA di hari perdagangan berikutnya? Hasilnya dibandingkan
dengan base rate dari seluruh universe buat ngukur "lift" -- apakah skor tinggi
beneran lebih sering diikuti ARA besoknya dibanding pilih saham random.

Ini BUKAN jaminan strategi profitable. Backtest ini nggak masukin biaya
transaksi, likuiditas eksekusi riil, survivorship bias (saham yang sudah
delisting nggak kehitung karena cuma menguji saham yang listed sekarang), atau
bahwa hasil masa lalu menjamin masa depan.
"""

from __future__ import annotations

import pandas as pd

from . import accumulation, rules

# Perlu WINDOW hari histori buat CMF/OBV pertama kali, + 1 hari buat prev_close, + 1 hari
# buat ngecek hasil besoknya.
MIN_HISTORY_FOR_EVAL = accumulation.WINDOW + 2


def _evaluate_stock(kode: str, df: pd.DataFrame) -> list[dict]:
    df = df.sort_index().dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    rows: list[dict] = []
    n = len(df)
    if n < MIN_HISTORY_FOR_EVAL:
        return rows

    for i in range(accumulation.WINDOW, n - 1):
        slice_ = df.iloc[: i + 1]
        today = slice_.iloc[-1]
        prev_close = float(slice_.iloc[-2]["Close"])
        if prev_close <= 0:
            continue

        vol_window = slice_.iloc[-21:-1]["Volume"]
        avg_volume_20 = float(vol_window.mean()) if len(vol_window) > 0 else float("nan")
        today_volume = float(today["Volume"])
        volume_ratio = today_volume / avg_volume_20 if avg_volume_20 else float("nan")
        likuid = bool(pd.notna(volume_ratio) and volume_ratio >= accumulation.MIN_VOLUME_RATIO)

        cmf_20 = accumulation.chaikin_money_flow(slice_)
        obv_trend_20 = accumulation.obv_trend(slice_)
        price_change_20d = accumulation.price_change_over(slice_)
        skor_mentah = accumulation.accumulation_score(cmf_20, obv_trend_20, price_change_20d)

        today_close = float(today["Close"])
        band = rules.get_band(today_close)
        limit_ara_besok = today_close * (1 + band.ara_pct)

        besok = df.iloc[i + 1]
        besok_high = float(besok["High"])
        besok_close = float(besok["Close"])
        # Toleransi 0.1% buat pembulatan fraksi harga riil vs limit hasil hitungan kita.
        kena_ara_besok = max(besok_high, besok_close) >= limit_ara_besok * 0.999

        rows.append(
            {
                "kode": kode,
                "tanggal": slice_.index[-1],
                "volume_ratio": volume_ratio,
                "akumulasi_likuid": likuid,
                "skor_akumulasi_mentah": skor_mentah,
                "kena_ara_besok": kena_ara_besok,
            }
        )
    return rows


def _pct_rank_liquid(group: pd.DataFrame) -> pd.Series:
    liquid = group["akumulasi_likuid"]
    out = pd.Series(float("nan"), index=group.index)
    if liquid.any():
        out[liquid] = group.loc[liquid, "skor_akumulasi_mentah"].rank(pct=True) * 100
    return out


def run_backtest(price_history: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Hasil satu baris per (saham, hari) yang dievaluasi, dengan persentil akumulasi
    dihitung cross-sectional per hari (relatif ke saham lain yang likuid hari itu),
    persis kayak cara kerja tab Akumulasi di dashboard."""
    all_rows: list[dict] = []
    for kode, df in price_history.items():
        all_rows.extend(_evaluate_stock(kode, df))

    result = pd.DataFrame(all_rows)
    if result.empty:
        return result

    result["skor_akumulasi_persentil"] = result.groupby("tanggal", group_keys=False).apply(
        _pct_rank_liquid
    )
    return result


def summarize(result: pd.DataFrame, persentil_threshold: float = 80.0) -> dict:
    if result.empty:
        return {}

    base_rate = result["kena_ara_besok"].mean()
    top = result[result["skor_akumulasi_persentil"] >= persentil_threshold]
    top_rate = top["kena_ara_besok"].mean() if not top.empty else float("nan")

    return {
        "n_observasi": len(result),
        "n_hari": int(result["tanggal"].nunique()),
        "n_saham": int(result["kode"].nunique()),
        "base_rate_pct": base_rate * 100,
        "top_rate_pct": top_rate * 100 if pd.notna(top_rate) else float("nan"),
        "n_top": len(top),
        "n_top_hit": int(top["kena_ara_besok"].sum()) if not top.empty else 0,
        "lift": (top_rate / base_rate) if base_rate and pd.notna(top_rate) else float("nan"),
    }
