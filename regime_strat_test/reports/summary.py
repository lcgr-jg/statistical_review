"""Console + CSV report helpers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def print_report(name: str, analysis: dict, folds: pd.DataFrame, stress: pd.DataFrame) -> None:
    print("\n" + "=" * 72)
    print(f"STRATEGY: {name}")
    print("=" * 72)
    print("\n-- Regime buckets (entry state) --")
    print(analysis["buckets"].to_string(index=False))
    print("\n-- PnL ~ regime_value regression --")
    reg = analysis["regression"]
    if "error" in reg:
        print(reg)
    else:
        print(f"n={reg['n']}")
        print("linear:", reg["linear"])
        print("quadratic:", reg["quadratic"])
        print("suggests_threshold_nonlinearity:", reg["suggests_threshold_nonlinearity"])
    if folds is not None and not folds.empty:
        print("\n-- Walk-forward OOS folds --")
        print(folds.to_string(index=False))
    if stress is not None and not stress.empty:
        print("\n-- Stress windows --")
        print(stress.to_string(index=False))


def save_report(
    out_dir: Path,
    name: str,
    trades: pd.DataFrame,
    analysis: dict,
    folds: pd.DataFrame,
    oos: pd.DataFrame,
    stress: pd.DataFrame,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(out_dir / f"{name}_trades.csv", index=False)
    analysis["buckets"].to_csv(out_dir / f"{name}_buckets.csv", index=False)
    if folds is not None and not folds.empty:
        folds.to_csv(out_dir / f"{name}_walkforward.csv", index=False)
    if oos is not None and not oos.empty:
        oos.to_csv(out_dir / f"{name}_oos_trades.csv", index=False)
    if stress is not None and not stress.empty:
        stress.to_csv(out_dir / f"{name}_stress.csv", index=False)
    # regression as small text
    (out_dir / f"{name}_regression.txt").write_text(str(analysis["regression"]), encoding="utf-8")
