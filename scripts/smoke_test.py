"""Smoke test tanpa akses internet: pakai data harga palsu untuk cek pipeline."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

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


universe = pd.DataFrame(
    {"kode": ["AAAA", "BBBB", "CCCC"], "nama": ["Test A", "Test B", "Test C"], "papan": ["Utama"] * 3}
)

history = {
    "AAAA": fake_history(prev_close=1000, last_price=1240, volume=5_000_000),  # near ARA (25% band)
    "BBBB": fake_history(prev_close=100, last_price=105, volume=100_000),  # far from ARA
    "CCCC": fake_history(prev_close=6000, last_price=7200, volume=2_000_000),  # exactly at ARA (20% band)
}

summary = data_mod.build_summary(history, universe)
print(summary[["kode", "prev_close", "harga_terakhir", "batas_ara_pct", "harga_limit_ara",
               "progress_ke_ara_pct", "volume_ratio", "skor_potensi"]].to_string(index=False))

assert rules.get_band(150).ara_pct == 0.35
assert rules.get_band(200).ara_pct == 0.35
assert rules.get_band(201).ara_pct == 0.25
assert rules.get_band(5000).ara_pct == 0.25
assert rules.get_band(5001).ara_pct == 0.20
assert all(rules.get_band(p).arb_pct == 0.15 for p in [150, 200, 5000, 6000])

row_c = summary[summary["kode"] == "CCCC"].iloc[0]
assert abs(row_c["progress_ke_ara_pct"] - 100) < 0.5, row_c["progress_ke_ara_pct"]

print("\nOK: semua assertion lolos.")
