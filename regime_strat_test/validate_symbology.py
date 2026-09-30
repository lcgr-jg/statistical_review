"""
Probe Bloomberg tickers used by the backtest and write a short validation report.

Usage:
  python validate_symbology.py              # desktop session
  python validate_symbology.py --on-server  # BPIPE
  python validate_symbology.py --years 2    # shorter hist window
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import (
    ATM_IV_TICKERS,
    ICE_CURVE,
    INVENTORY_TICKERS,
    IV_FIELD,
    PRICE_FIELD,
    US_CURVE,
)


def _probe_hist(bbg, ticker: str, field: str, start: datetime, end: datetime) -> dict:
    try:
        df = bbg.fetch_hist(ticker, field, p_start=start, p_end=end, p_pd_datetime=True)
    except Exception as e:
        return {"ticker": ticker, "field": field, "ok": False, "n": 0, "error": str(e)}
    if df is None or df.empty:
        return {"ticker": ticker, "field": field, "ok": False, "n": 0, "error": "empty"}
    col = f"{ticker}_{field}"
    if col not in df.columns:
        cols = [c for c in df.columns if field in str(c)]
        col = cols[0] if cols else df.columns[0]
    s = df[col].dropna()
    return {
        "ticker": ticker,
        "field": field,
        "ok": len(s) > 0,
        "n": int(len(s)),
        "start": str(s.index.min().date()) if len(s) else None,
        "end": str(s.index.max().date()) if len(s) else None,
        "last": float(s.iloc[-1]) if len(s) else None,
        "error": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--on-server", action="store_true")
    ap.add_argument("--years", type=int, default=2)
    args = ap.parse_args()

    from bloomberg import BBGQuery

    end = datetime.today()
    start = end - timedelta(days=365 * args.years)
    print(f"Connecting ({'BPIPE' if args.on_server else 'desktop'}) {start.date()} -> {end.date()}")
    bbg = BBGQuery(p_on_server=args.on_server)

    tickers = []
    # front two months + a mid curve point for each product
    for book in (US_CURVE, ICE_CURVE):
        for product, chain in book.items():
            for t in (chain[0], chain[1], chain[min(5, len(chain) - 1)]):
                tickers.append((t, PRICE_FIELD, f"curve:{product}"))
    for product, t in INVENTORY_TICKERS.items():
        tickers.append((t, PRICE_FIELD, f"inv:{product}"))
    for product, t in ATM_IV_TICKERS.items():
        tickers.append((t, IV_FIELD, f"iv:{product}"))
        # alternate field often used on desks
        tickers.append((t, "IVOL_MID", f"iv_alt:{product}"))

    rows = []
    for ticker, field, tag in tickers:
        print(f"  probing {tag:12s} {ticker:20s} {field} ...", end=" ", flush=True)
        r = _probe_hist(bbg, ticker, field, start, end)
        r["tag"] = tag
        rows.append(r)
        status = "OK" if r["ok"] else f"FAIL ({r['error']})"
        extra = f"n={r['n']} last={r['last']}" if r["ok"] else ""
        print(f"{status} {extra}")

    import pandas as pd

    report = pd.DataFrame(rows)
    out = ROOT / "output" / "symbology_validation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(out, index=False)
    print(f"\nWrote {out}")
    print("\nSummary by tag:")
    print(report.groupby("tag")["ok"].mean().rename("pct_ok").to_string())
    bad = report[~report["ok"]]
    if not bad.empty:
        print("\nFailed probes — update config.py tickers/fields:")
        print(bad[["tag", "ticker", "field", "error"]].to_string(index=False))
    else:
        print("\nAll probes returned data.")


if __name__ == "__main__":
    main()
