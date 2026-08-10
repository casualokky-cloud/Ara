"""
Indikator akumulasi teknikal dari data harga & volume (OHLCV) saja.

INI BUKAN bandarmology (data broker net buy). Bandarmology butuh data broker
summary yang tidak tersedia lewat yfinance — lihat README bagian
"Soal bandarmology" untuk opsi ke depannya. Modul ini cuma memakai dua
indikator teknikal klasik yang bisa dihitung dari OHLCV:

  - Chaikin Money Flow (CMF): tekanan beli/jual berdasarkan di mana harga
    closing berada dalam range high-low tiap hari, dibobot volume, lalu
    dirata-rata selama N hari. CMF > 0 = tekanan beli (akumulasi),
    CMF < 0 = tekanan jual (distribusi).
  - OBV (On-Balance Volume) trend: apakah volume selama N hari terakhir
    net condong ke hari-hari naik (dijumlah) atau hari-hari turun
    (dikurang), dinormalisasi ke satuan "hari rata-rata volume".

Kombinasi CMF & OBV tinggi SAAT harga masih relatif flat/belum breakout
adalah pola klasik "akumulasi diam-diam sebelum harga bergerak" — kandidat
early-entry. Ini kebalikan dari skor "Potensi ARA" di scoring.py yang
justru menandai saham yang HARGANYA SUDAH bergerak hari itu.

PERINGATAN SOAL SAHAM TIPIS: CMF & OBV cuma lihat "di mana closing mendarat
dalam range high-low", dikali volume — bukan siapa yang beli/jual beneran.
Pas volume hari itu jauh di bawah rata-rata (Volume Ratio rendah), sinyalnya
gampang disesatkan segelintir transaksi kecil, apalagi di saham harga rendah
yang tipis diperdagangkan (rawan "digoreng"). Kasus nyata: MKTR pernah
nangkring persentil 100 di sini padahal broker summary riilnya (Stockbit)
nunjukin "Big Distribution", justru pas Volume Ratio-nya cuma 0.11x —
volume terlalu tipis buat sinyal CMF/OBV dipercaya. Makanya ada
MIN_VOLUME_RATIO di bawah: saham dengan Volume Ratio di bawah itu dikeluarkan
dari ranking persentil sama sekali, bukan cuma diturunkan skornya.
"""

from __future__ import annotations

import math

import pandas as pd

WINDOW = 20
MIN_VOLUME_RATIO = 0.3


def chaikin_money_flow(df: pd.DataFrame, window: int = WINDOW) -> float:
    high, low, close, volume = df["High"], df["Low"], df["Close"], df["Volume"]
    price_range = (high - low).replace(0, float("nan"))
    money_flow_multiplier = ((close - low) - (high - close)) / price_range
    money_flow_volume = (money_flow_multiplier * volume).iloc[-window:]
    volume_sum = volume.iloc[-window:].sum()
    if not volume_sum or money_flow_volume.isna().all():
        return float("nan")
    return float(money_flow_volume.sum() / volume_sum)


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = df["Close"].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (direction * df["Volume"]).fillna(0).cumsum()


def obv_trend(df: pd.DataFrame, window: int = WINDOW) -> float:
    """Perubahan OBV selama `window` hari, dalam satuan hari rata-rata volume."""
    obv_series = _obv(df)
    if len(obv_series) <= window:
        return float("nan")
    change = obv_series.iloc[-1] - obv_series.iloc[-window - 1]
    avg_volume = df["Volume"].iloc[-window:].mean()
    if not avg_volume:
        return float("nan")
    return float(change / avg_volume)


def price_change_over(df: pd.DataFrame, window: int = WINDOW) -> float:
    closes = df["Close"]
    if len(closes) <= window:
        return float("nan")
    start = float(closes.iloc[-window - 1])
    end = float(closes.iloc[-1])
    if not start:
        return float("nan")
    return (end - start) / start * 100


def _clamp01(value: float, low: float, high: float) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def accumulation_score(cmf: float, obv_trend_value: float, price_change_pct: float) -> float:
    cmf_score = _clamp01(cmf, -0.3, 0.3) * 50

    obv_score = _clamp01(obv_trend_value, -5, 5) * 30

    already_run_up = max(price_change_pct, 0) if not math.isnan(price_change_pct) else 0
    quiet_bonus = max(0.0, 1 - already_run_up / 40) * 20

    return round(cmf_score + obv_score + quiet_bonus, 1)
