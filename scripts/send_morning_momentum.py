"""
Ambil ringkasan tab "Momentum Hari Ini" dan kirim sebagai email pagi.

Dijalankan otomatis oleh GitHub Actions (.github/workflows/morning-momentum-email.yml)
tiap hari kerja jam 09:05 WIB (~5 menit setelah market IDX buka). Bisa juga dijalankan
manual buat testing:

    SMTP_USERNAME=xxx@gmail.com SMTP_PASSWORD=app-password EMAIL_TO=xxx@gmail.com \
        python scripts/send_morning_momentum.py

Butuh 3 environment variable (di GitHub Actions: repository secrets):
  - SMTP_USERNAME: alamat Gmail pengirim
  - SMTP_PASSWORD: App Password Gmail (BUKAN password akun biasa)
  - EMAIL_TO: alamat tujuan
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ara_screener import data as data_mod  # noqa: E402

MOMENTUM_THRESHOLD = float(os.environ.get("MOMENTUM_THRESHOLD", "50"))
BOARD_FILTER = {"Utama"}  # samain sama default filter papan di dashboard

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TICKERS_PATH = os.path.join(REPO_ROOT, "data", "idx_tickers.csv")


def build_email_html(momentum) -> str:
    if momentum.empty:
        body = f"<p>Nggak ada saham dengan skor Momentum &ge; {MOMENTUM_THRESHOLD:.0f} pagi ini.</p>"
    else:
        rows_html = ""
        for _, row in momentum.iterrows():
            rows_html += (
                "<tr>"
                f"<td>{row['kode']}</td>"
                f"<td>{row['nama']}</td>"
                f"<td style='text-align:right'>{row['harga_terakhir']:,.0f}</td>"
                f"<td style='text-align:right'>{row['perubahan_pct']:+.2f}%</td>"
                f"<td style='text-align:right'>{row['progress_ke_ara_pct']:.1f}%</td>"
                f"<td style='text-align:right'>{row['volume_ratio']:.2f}x</td>"
                f"<td style='text-align:right'><b>{row['skor_potensi']:.1f}</b></td>"
                "</tr>"
            )
        body = f"""
        <p>{len(momentum)} saham dengan skor Momentum &ge; {MOMENTUM_THRESHOLD:.0f}.</p>
        <table border="1" cellpadding="6" cellspacing="0"
               style="border-collapse:collapse;font-family:sans-serif;font-size:13px">
          <tr style="background:#111;color:#fff">
            <th>Kode</th><th>Nama</th><th>Harga</th><th>% Chg</th>
            <th>Progress ARA</th><th>Vol Ratio</th><th>Skor Momentum</th>
          </tr>
          {rows_html}
        </table>
        """

    return f"""
    <div style="font-family:sans-serif">
      {body}
      <p style="color:#888;font-size:12px">
        Data diambil ~5 menit setelah market buka &mdash; volume &amp; momentum masih tipis
        segitu awal, angkanya bisa berubah drastis sepanjang hari. Bukan nasihat keuangan.
        Skor Momentum murni heuristik rule-based dari harga/volume, belum divalidasi/backtest
        terhadap histori ARA riil.
      </p>
    </div>
    """


def main() -> None:
    smtp_username = os.environ["SMTP_USERNAME"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    email_to = os.environ["EMAIL_TO"]

    universe = data_mod.load_ticker_universe(TICKERS_PATH)
    universe = universe[universe["papan"].isin(BOARD_FILTER)]
    kodes = sorted(universe["kode"].dropna().unique().tolist())

    history = data_mod.fetch_price_history(kodes)
    summary = data_mod.build_summary(history, universe)

    momentum = summary[summary["skor_potensi"] >= MOMENTUM_THRESHOLD].sort_values(
        "skor_potensi", ascending=False
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"ARA Screener - Momentum Hari Ini ({len(momentum)} saham)"
    msg["From"] = smtp_username
    msg["To"] = email_to
    msg.attach(MIMEText(build_email_html(momentum), "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

    print(f"Email terkirim ke {email_to}: {len(momentum)} saham dengan skor >= {MOMENTUM_THRESHOLD}.")


if __name__ == "__main__":
    main()
