"""Unconditional + regime-bucketed metrics and continuous PnL~regime regression."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MetricBundle:
    n: int
    hit_rate: float
    avg_pnl: float
    total_pnl: float
    sharpe: float
    avg_pnl_net: float
    sharpe_net: float


def _sharpe(pnl: pd.Series, annualization: int = 252) -> float:
    """Trade-level Sharpe: mean/std of trade PnL, scaled by sqrt(trades/year proxy)."""
    x = pnl.dropna()
    if len(x) < 2 or x.std(ddof=1) == 0:
        return 0.0
    # scale by sqrt(N) so more frequent strategies aren't mechanically lower
    return float(x.mean() / x.std(ddof=1) * np.sqrt(min(len(x), annualization)))


def summarize(pnl: pd.Series, pnl_net: pd.Series | None = None, annualization: int = 252) -> MetricBundle:
    pnl_net = pnl if pnl_net is None else pnl_net
    n = int(pnl.notna().sum())
    hits = (pnl > 0).sum()
    return MetricBundle(
        n=n,
        hit_rate=float(hits / n) if n else 0.0,
        avg_pnl=float(pnl.mean()) if n else 0.0,
        total_pnl=float(pnl.sum()) if n else 0.0,
        sharpe=_sharpe(pnl, annualization),
        avg_pnl_net=float(pnl_net.mean()) if n else 0.0,
        sharpe_net=_sharpe(pnl_net, annualization),
    )


def bucket_metrics(trades: pd.DataFrame, annualization: int = 252) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    # unconditional
    u = summarize(trades["pnl"], trades["pnl_net"], annualization)
    rows.append({"bucket": "UNCONDITIONAL", **u.__dict__})
    for state, g in trades.groupby(trades["regime_state"].fillna("na")):
        m = summarize(g["pnl"], g["pnl_net"], annualization)
        rows.append({"bucket": str(state), **m.__dict__})
    return pd.DataFrame(rows)


def regress_pnl_on_regime(trades: pd.DataFrame) -> dict:
    """
    OLS: pnl_net ~ regime_value  (+ optional quadratic).
    Uses statsmodels if available; else numpy lstsq fallback.
    """
    df = trades.dropna(subset=["pnl_net", "regime_value"]).copy()
    if len(df) < 10:
        return {"error": "insufficient observations", "n": len(df)}

    y = df["pnl_net"].values.astype(float)
    x = df["regime_value"].values.astype(float)
    x2 = x ** 2

    def _ols(X, y):
        X = np.column_stack([np.ones(len(X)), X]) if X.ndim == 1 else np.column_stack([np.ones(len(X)), X])
        beta, residuals, _, _ = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ beta
        ss_res = ((y - yhat) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        # crude t-stats
        n, k = X.shape
        dof = max(n - k, 1)
        sigma2 = ss_res / dof
        try:
            cov = sigma2 * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.diag(cov))
            t = beta / se
        except np.linalg.LinAlgError:
            se = np.full_like(beta, np.nan)
            t = np.full_like(beta, np.nan)
        return beta, se, t, r2, n

    b1, se1, t1, r2_lin, n = _ols(x, y)
    b2, se2, t2, r2_quad, _ = _ols(np.column_stack([x, x2]), y)

    out = {
        "n": n,
        "linear": {
            "alpha": float(b1[0]),
            "beta": float(b1[1]),
            "t_beta": float(t1[1]),
            "r2": float(r2_lin),
        },
        "quadratic": {
            "alpha": float(b2[0]),
            "beta": float(b2[1]),
            "beta2": float(b2[2]),
            "t_beta": float(t2[1]),
            "t_beta2": float(t2[2]),
            "r2": float(r2_quad),
        },
    }
    # Heuristic: quadratic term matters if |t| > 1.96 and R² lift > 0.02
    out["suggests_threshold_nonlinearity"] = bool(
        abs(out["quadratic"]["t_beta2"]) > 1.96
        and (out["quadratic"]["r2"] - out["linear"]["r2"]) > 0.02
    )

    try:
        import statsmodels.api as sm

        X = sm.add_constant(df[["regime_value"]])
        model = sm.OLS(df["pnl_net"], X, missing="drop").fit()
        out["statsmodels_linear"] = {
            "params": model.params.to_dict(),
            "tvalues": model.tvalues.to_dict(),
            "pvalues": model.pvalues.to_dict(),
            "rsquared": float(model.rsquared),
        }
    except Exception:
        pass
    return out


def analyze_trades(trades: pd.DataFrame, annualization: int = 252) -> dict:
    return {
        "buckets": bucket_metrics(trades, annualization),
        "regression": regress_pnl_on_regime(trades),
    }
