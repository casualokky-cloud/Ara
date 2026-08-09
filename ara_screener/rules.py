"""
Aturan batas Auto Rejection Atas (ARA) & Auto Rejection Bawah (ARB) di BEI.

Berlaku sejak 8 April 2025 (auto rejection asimetris):
  - Harga acuan Rp50 - Rp200      -> ARA 35%
  - Harga acuan >Rp200 - Rp5.000  -> ARA 25%
  - Harga acuan >Rp5.000          -> ARA 20%
  - ARB seragam 15% untuk semua rentang harga.

Catatan: harga limit hasil hitungan di sini BELUM dibulatkan ke fraksi harga
(tick size) resmi BEI, jadi bisa berbeda beberapa rupiah dari harga ARA/ARB
riil di sistem perdagangan. Cukup akurat untuk screening, jangan dipakai
sebagai acuan pasang order.

Sumber: Keputusan Direksi BEI terkait auto rejection asimetris, per 8 April 2025.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AutoRejectBand:
    ara_pct: float
    arb_pct: float


def get_band(prev_close: float) -> AutoRejectBand:
    """Kembalikan persentase batas ARA/ARB berdasarkan harga acuan (previous close)."""
    if prev_close <= 200:
        ara_pct = 0.35
    elif prev_close <= 5000:
        ara_pct = 0.25
    else:
        ara_pct = 0.20
    return AutoRejectBand(ara_pct=ara_pct, arb_pct=0.15)


def ara_price(prev_close: float) -> float:
    band = get_band(prev_close)
    return prev_close * (1 + band.ara_pct)


def arb_price(prev_close: float) -> float:
    band = get_band(prev_close)
    return prev_close * (1 - band.arb_pct)
