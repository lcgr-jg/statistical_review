"""
CLI entry for regime-conditional commodity backtests.

Examples
--------
  # Offline smoke test (synthetic data)
  python run_backtest.py --demo --strategies cash_and_carry,calendar_spread,crack_mr

  # Live / cached Bloomberg
  python run_backtest.py --complex BOTH --strategies cash_and_carry,calendar_spread,crack_mr,vol_calendar,seasonal_inventory,crack_skew
  python run_backtest.py --refresh-cache --on-server
  python run_backtest.py --holding fixed_days --hold-days 20
  python run_backtest.py --holding weekly
  python run_backtest.py --holding regime_exit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import BacktestConfig, HoldingConfig, HoldingMode
from data.synthetic import make_synthetic_complex
from engine.backtest import load_market_data, run_strategy
from engine.regime_analytics import analyze_trades
from engine.stress import stress_panels
from engine.walk_forward import oos_bucket_summary, walk_forward_thresholds
from reports.summary import print_report, save_report
from strategies import STRATEGY_REGISTRY


DEFAULT_STRATS = [
    "cash_and_carry",
    "calendar_spread",
    "crack_mr",
    "vol_calendar",
    "seasonal_inventory",
    "crack_skew",
]


def parse_args():
    p = argparse.ArgumentParser(description="Regime-conditional commodity backtest")
    p.add_argument("--demo", action="store_true", help="Use synthetic data (no Bloomberg)")
    p.add_argument("--complex", default="BOTH", choices=["US", "ICE", "BOTH"])
    p.add_argument(
        "--strategies",
        default=",".join(DEFAULT_STRATS),
        help="Comma-separated strategy keys",
    )
    p.add_argument("--product", default="CL", help="Primary product for curve strategies")
    p.add_argument("--holding", default="fixed_days", choices=[m.value for m in HoldingMode])
    p.add_argument("--hold-days", type=int, default=20)
    p.add_argument("--refresh-cache", action="store_true")
    p.add_argument("--on-server", action="store_true", help="Use BPIPE server session")
    p.add_argument("--out", default=str(ROOT / "output"))
    p.add_argument("--crack-complex", default="US", choices=["US", "ICE"])
    return p.parse_args()


def build_strategy(key: str, args, holding: HoldingConfig):
    cls = STRATEGY_REGISTRY[key]
    if key == "gex_fade":
        return cls(holding=holding, product=args.product)
    if key == "crack_mr":
        return cls(holding=holding, product=args.product, complex_name=args.crack_complex)
    if key == "crack_skew":
        return cls(holding=holding)
    return cls(holding=holding, product=args.product)


def main():
    args = parse_args()
    holding = HoldingConfig(mode=HoldingMode(args.holding), hold_days=args.hold_days)
    cfg = BacktestConfig(
        complex=args.complex,
        holding=holding,
        refresh_cache=args.refresh_cache,
        on_server=args.on_server,
    )

    if args.demo:
        print("Using SYNTHETIC data (--demo). Not for research.")
        data = make_synthetic_complex()
    else:
        print("Loading market data (cache-aware Bloomberg pulls)...")
        data = load_market_data(cfg)

    keys = [k.strip() for k in args.strategies.split(",") if k.strip()]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for key in keys:
        if key not in STRATEGY_REGISTRY:
            print(f"Unknown strategy '{key}', skipping. Known: {list(STRATEGY_REGISTRY)}")
            continue
        if key == "gex_fade":
            print(f"\n[{key}] deferred to v2 — skipping.")
            continue

        strat = build_strategy(key, args, holding)
        # vol strategies: ensure we don't silently run on empty IV
        if key == "vol_calendar" and (data.get("iv") is None or data["iv"].empty):
            print(f"[{key}] no IV history — skip (check VOL_START / Bloomberg field).")
            continue

        print(f"\nRunning {key} ...")
        try:
            trades = run_strategy(strat, data)
        except NotImplementedError as e:
            print(f"[{key}] {e}")
            continue

        if trades.empty:
            print(f"[{key}] no trades generated.")
            continue

        analysis = analyze_trades(trades, cfg.annualization)
        folds, oos = walk_forward_thresholds(trades, cfg=cfg.walk_forward)
        if not oos.empty:
            print("\n-- Walk-forward bucket summary (OOS) --")
            print(oos_bucket_summary(oos).to_string(index=False))
        stress = stress_panels(trades)
        print_report(key, analysis, folds, stress)
        save_report(out_dir, key, trades, analysis, folds, oos, stress)
        print(f"Wrote CSVs under {out_dir}")


if __name__ == "__main__":
    main()
