"""Smoke test tanpa akses internet: pakai data harga palsu untuk cek pipeline."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ara_screener import accumulation, backtest
from ara_screener import data as data_mod
from ara_screener import rules

np.random.seed(0)


def fake_history(prev_close: float, last_price: float, volume: float) -> pd.DataFrame:
    dates = pd.date_range("2026-06-01", periods=25, freq="B")
    closes = np.linspace(prev_close * 0.85, prev_close, len(dates) - 1)
    closes = np.append(closes, last_price)
    opens = closes * 0.995
    highs = np.maximum(opens, closes) * 1.01
    lows = np.minimum(opens, closes) * 0.99
    volumes = np.full(len(dates), volume / 2)
    volumes[-1] = volume
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=dates,
    )


def fake_accumulation_history(quiet: bool, thin_last_day: bool = False) -> pd.DataFrame:
    """quiet=True -> harga flat, closing dekat high, volume naik (pola akumulasi).
    quiet=False -> harga flat, closing dekat low, volume datar (kontrol/distribusi).
    thin_last_day=True -> volume hari terakhir dibikin jauh di bawah rata-rata (kasus MKTR:
    pola CMF/OBV keliatan bagus tapi volumenya terlalu tipis buat dipercaya)."""
    dates = pd.date_range("2026-06-01", periods=25, freq="B")
    n = len(dates)
    closes = np.full(n, 500.0) + np.sin(np.linspace(0, 3, n))  # nyaris flat
    if quiet:
        highs = closes + 1  # closing dekat high -> CMF positif
        lows = closes - 5
        volumes = np.linspace(500_000, 1_500_000, n)  # volume naik
    else:
        highs = closes + 5  # closing dekat low -> CMF negatif
        lows = closes - 1
        volumes = np.full(n, 800_000.0)  # volume datar
    opens = (highs + lows) / 2
    if thin_last_day:
        volumes = volumes.copy()
        volumes[-1] = volumes[:-1].mean() * 0.05  # volume ratio ~0.05x, jauh di bawah MIN_VOLUME_RATIO
    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=dates,
    )


universe = pd.DataFrame(
    {
        "kode": ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF"],
        "nama": ["Test A", "Test B", "Test C", "Test D", "Test E", "Test F"],
        "papan": ["Utama"] * 6,
    }
)

history = {
    "AAAA": fake_history(prev_close=1000, last_price=1240, volume=5_000_000),  # near ARA (25% band)
    "BBBB": fake_history(prev_close=100, last_price=105, volume=100_000),  # far from ARA
    "CCCC": fake_history(prev_close=6000, last_price=7200, volume=2_000_000),  # exactly at ARA (20% band)
    "DDDD": fake_accumulation_history(quiet=True),  # pola akumulasi
    "EEEE": fake_accumulation_history(quiet=False),  # kontrol: bukan akumulasi
    "FFFF": fake_accumulation_history(quiet=True, thin_last_day=True),  # kasus MKTR: pola bagus, volume tipis
}

summary = data_mod.build_summary(history, universe)
print(summary[["kode", "prev_close", "harga_terakhir", "batas_ara_pct", "harga_limit_ara",
               "progress_ke_ara_pct", "volume_ratio", "skor_potensi"]].to_string(index=False))
print()
print(summary[["kode", "cmf_20", "obv_trend_20", "harga_20d_change_pct", "skor_akumulasi"]].to_string(index=False))

assert rules.get_band(150).ara_pct == 0.35
assert rules.get_band(200).ara_pct == 0.35
assert rules.get_band(201).ara_pct == 0.25
assert rules.get_band(5000).ara_pct == 0.25
assert rules.get_band(5001).ara_pct == 0.20
assert all(rules.get_band(p).arb_pct == 0.15 for p in [150, 200, 5000, 6000])

row_c = summary[summary["kode"] == "CCCC"].iloc[0]
assert abs(row_c["progress_ke_ara_pct"] - 100) < 0.5, row_c["progress_ke_ara_pct"]

skor_d = summary.loc[summary["kode"] == "DDDD", "skor_akumulasi"].iloc[0]
skor_e = summary.loc[summary["kode"] == "EEEE", "skor_akumulasi"].iloc[0]
assert skor_d > skor_e, f"DDDD (pola akumulasi) harus > EEEE (kontrol): {skor_d} vs {skor_e}"

row_f = summary[summary["kode"] == "FFFF"].iloc[0]
assert row_f["volume_ratio"] < 0.3, row_f["volume_ratio"]
assert not row_f["akumulasi_likuid"], "FFFF (volume tipis) harusnya ditandai nggak likuid"
assert pd.isna(row_f["skor_akumulasi"]), (
    f"FFFF (kasus MKTR: pola bagus tapi volume tipis) harus dikeluarkan dari ranking "
    f"(skor_akumulasi NaN), malah dapet {row_f['skor_akumulasi']}"
)

print("\nOK: semua assertion lolos.")


def fake_backtest_history(quiet: bool, jump_every: int | None) -> pd.DataFrame:
    """quiet=True -> pola akumulasi (closing dekat high, volume naik) di sepanjang histori.
    quiet=False -> pola distribusi (kontrol), nggak pernah dikasih lonjakan ARA.
    jump_every -> tiap N hari evaluasi, hari BERIKUTNYA dipaksa lompat +30% (kena ARA)."""
    dates = pd.date_range("2026-01-05", periods=50, freq="B")
    n = len(dates)
    closes = np.full(n, 500.0) + np.sin(np.linspace(0, 6, n)) * 2
    if quiet:
        highs = closes + 1
        lows = closes - 5
        volumes = np.linspace(500_000, 1_500_000, n)
    else:
        highs = closes + 5
        lows = closes - 1
        volumes = np.full(n, 800_000.0)
    opens = (highs + lows) / 2
    closes, highs, lows, opens = closes.copy(), highs.copy(), lows.copy(), opens.copy()

    if jump_every:
        for i in range(accumulation.WINDOW, n - 1):
            if (i - accumulation.WINDOW) % jump_every == 0:
                jump_close = closes[i] * 1.30  # jauh di atas batas ARA tier ini (25%)
                closes[i + 1] = jump_close
                highs[i + 1] = max(highs[i + 1], jump_close)
                lows[i + 1] = min(lows[i + 1], jump_close)
                opens[i + 1] = jump_close

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=dates,
    )


bt_history = {
    "JJJJ": fake_backtest_history(quiet=True, jump_every=5),  # akumulasi, sering lanjut ARA
    "KKKK": fake_backtest_history(quiet=True, jump_every=5),  # akumulasi, sering lanjut ARA
    "LLLL": fake_backtest_history(quiet=False, jump_every=None),  # distribusi, nggak pernah ARA
    "MMMM": fake_backtest_history(quiet=False, jump_every=None),  # distribusi, nggak pernah ARA
}

bt_result = backtest.run_backtest(bt_history)
assert not bt_result.empty, "Backtest harusnya menghasilkan observasi dari data uji ini"

bt_summary = backtest.summarize(bt_result, persentil_threshold=80)
print(
    f"\nBacktest: n_observasi={bt_summary['n_observasi']} "
    f"base_rate={bt_summary['base_rate_pct']:.1f}% "
    f"top_rate={bt_summary['top_rate_pct']:.1f}% "
    f"lift={bt_summary['lift']:.2f}x"
)
assert bt_summary["top_rate_pct"] > bt_summary["base_rate_pct"], (
    "Saham berpola akumulasi (JJJJ/KKKK) seharusnya mendominasi persentil atas dan "
    f"punya hit rate lebih tinggi dari base rate: {bt_summary['top_rate_pct']} vs "
    f"{bt_summary['base_rate_pct']}"
)

print("OK: backtest assertion lolos.")
