"""Smoke test tanpa akses internet: pakai data harga palsu untuk cek pipeline."""

import datetime as _dt
import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from ara_screener import accumulation, backtest
from ara_screener import data as data_mod
from ara_screener import rules

np.random.seed(0)


def fake_history(prev_close: float, last_price: float, volume: float, lag_days: int = 0) -> pd.DataFrame:
    dates = pd.date_range("2026-06-01", periods=25, freq="B") - pd.tseries.offsets.BDay(lag_days)
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
        "kode": ["AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF", "NNNN"],
        "nama": ["Test A", "Test B", "Test C", "Test D", "Test E", "Test F", "Test N"],
        "papan": ["Utama"] * 7,
    }
)

history = {
    "AAAA": fake_history(prev_close=1000, last_price=1240, volume=5_000_000),  # near ARA (25% band)
    "BBBB": fake_history(prev_close=100, last_price=105, volume=100_000),  # far from ARA
    "CCCC": fake_history(prev_close=6000, last_price=7200, volume=2_000_000),  # exactly at ARA (20% band)
    "DDDD": fake_accumulation_history(quiet=True),  # pola akumulasi
    "EEEE": fake_accumulation_history(quiet=False),  # kontrol: bukan akumulasi
    "FFFF": fake_accumulation_history(quiet=True, thin_last_day=True),  # kasus MKTR: pola bagus, volume tipis
    "NNNN": fake_history(prev_close=300, last_price=310, volume=1_000_000, lag_days=1),  # yfinance belum update
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

row_a = summary[summary["kode"] == "AAAA"].iloc[0]
row_n = summary[summary["kode"] == "NNNN"].iloc[0]
assert row_a["data_terkini"], "AAAA (mayoritas) harusnya data_terkini=True"
assert not row_n["data_terkini"], (
    "NNNN (bar terakhirnya 1 hari lebih tua, simulasi yfinance belum update) "
    "harusnya ketandai data_terkini=False"
)
assert row_n["tanggal_data"] != row_a["tanggal_data"]
print(
    f"OK: filter data_terkini nangkep NNNN sebagai stale "
    f"(tanggal_data={row_n['tanggal_data']} vs acuan={row_a['tanggal_data']})."
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


kalender_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kalender_penting.csv")
kalender = pd.read_csv(kalender_path, parse_dates=["tanggal_mulai", "tanggal_selesai"])

REQUIRED_KALENDER_COLS = {"tanggal_mulai", "tanggal_selesai", "event", "kategori", "catatan", "sumber"}
assert REQUIRED_KALENDER_COLS.issubset(kalender.columns), kalender.columns.tolist()
assert not kalender.empty, "kalender_penting.csv kosong"
assert kalender["tanggal_mulai"].notna().all(), "ada tanggal_mulai yang gagal di-parse"
assert kalender["tanggal_selesai"].notna().all(), "ada tanggal_selesai yang gagal di-parse"
assert (kalender["tanggal_selesai"] >= kalender["tanggal_mulai"]).all(), (
    "ada baris dengan tanggal_selesai sebelum tanggal_mulai"
)
assert kalender["sumber"].str.startswith("http").all(), "ada baris tanpa URL sumber yang valid"

print(f"OK: kalender_penting.csv valid ({len(kalender)} event).")


app_spec = importlib.util.spec_from_file_location(
    "ara_screener_app", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ara_screener", "app.py")
)
app_module = importlib.util.module_from_spec(app_spec)
app_spec.loader.exec_module(app_module)

_key = app_module._trading_day_key
_WIB = app_module.WIB

_before_cutoff = _dt.datetime(2026, 8, 10, 8, 29, tzinfo=_WIB)
_at_cutoff = _dt.datetime(2026, 8, 10, 8, 30, tzinfo=_WIB)
_late_same_day = _dt.datetime(2026, 8, 10, 23, 59, tzinfo=_WIB)
_next_midnight = _dt.datetime(2026, 8, 11, 0, 0, tzinfo=_WIB)

assert _key(_before_cutoff) == "2026-08-09", _key(_before_cutoff)
assert _key(_at_cutoff) == "2026-08-10", _key(_at_cutoff)
assert _key(_late_same_day) == "2026-08-10", _key(_late_same_day)
assert _key(_next_midnight) == "2026-08-10", _key(_next_midnight)

print("OK: _trading_day_key (reset cache screener jam 08:30 WIB) lolos semua assertion.")
