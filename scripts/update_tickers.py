"""
Perbarui data/idx_tickers.csv dan data/idx_lq45.csv dari sumber publik.

Jalankan dari mesin yang punya akses internet penuh ke GitHub:

    python scripts/update_tickers.py

Sumber: wildangunawan/Dataset-Saham-IDX (CC BY-NC 4.0, non-komersial dengan atribusi).
"""

from __future__ import annotations

import os
import urllib.request

BASE_URL = (
    "https://raw.githubusercontent.com/wildangunawan/Dataset-Saham-IDX/master/List%20Emiten"
)
TARGETS = {
    "all.csv": "data/idx_tickers.csv",
    "LQ45.csv": "data/idx_lq45.csv",
}


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for source_name, dest_relpath in TARGETS.items():
        url = f"{BASE_URL}/{source_name}"
        dest_path = os.path.join(repo_root, dest_relpath)
        print(f"Mengunduh {url} -> {dest_relpath}")
        urllib.request.urlretrieve(url, dest_path)
    print("Selesai.")


if __name__ == "__main__":
    main()
