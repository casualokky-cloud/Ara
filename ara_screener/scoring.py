"""
Skor heuristik "potensi ARA" (0-100).

Ini BUKAN prediksi, hanya penilaian berbasis aturan dari sinyal harga & volume
hari berjalan:
  - Proximity (35 pt): seberapa dekat harga saat ini ke harga limit ARA.
  - Volume (30 pt)    : rasio volume hari ini vs rata-rata 20 hari (lonjakan minat beli).
  - Gap up (20 pt)    : seberapa besar saham gap up dari harga acuan saat open.
  - Momentum (15 pt)  : jumlah hari beruntun naik (closing to closing).

Kombinasi ini menyaring saham yang sedang "panas" dan mendekati batas atas,
bukan alat untuk memastikan saham akan ARA. Selalu cek fundamental, berita
korporasi (rights issue, akuisisi, dsb.), dan volume order book sebelum
mengambil keputusan.
"""

from __future__ import annotations

import math


def _clamp(value: float, low: float, high: float) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return low
    return max(low, min(high, value))


def potential_score(row: dict) -> float:
    proximity = max(row.get("progress_ke_ara_pct", 0), row.get("high_progress_ke_ara_pct", 0))
    proximity_score = _clamp(proximity, 0, 100) / 100 * 35

    volume_ratio = row.get("volume_ratio", 0)
    volume_score = _clamp(volume_ratio, 0, 5) / 5 * 30

    gap_pct = row.get("gap_pct", 0)
    gap_score = _clamp(gap_pct, 0, 10) / 10 * 20

    streak = row.get("streak_naik", 0)
    momentum_score = _clamp(streak, 0, 5) / 5 * 15

    return round(proximity_score + volume_score + gap_score + momentum_score, 1)
