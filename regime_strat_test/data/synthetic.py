"""
Synthetic market data for offline smoke tests (no Bloomberg).

Shapes match the live loaders so strategies/engine can be exercised end-to-end.
Not for research conclusions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_complex(
    start: str = "2015-01-01",
    end: str = "2024-12-31",
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, end)
    n = len(idx)

    def _gbm(s0, vol, n):
        shocks = rng.normal(0, vol / np.sqrt(252), n)
        return s0 * np.exp(np.cumsum(shocks))

    cl_f1 = _gbm(70, 0.35, n)
    # oscillating contango/backwardation
    basis = 0.02 * np.sin(np.linspace(0, 30, n)) + rng.normal(0, 0.005, n)
    # Persistent crack residual so half-life regime is exerciseable in --demo
    crack_shock = np.zeros(n)
    for i in range(1, n):
        crack_shock[i] = 0.97 * crack_shock[i - 1] + rng.normal(0, 0.3)
    xb_f1 = cl_f1 / 42 + 0.15 + crack_shock / 42
    ho_f1 = cl_f1 / 42 + 0.20 + 0.5 * crack_shock / 42
    curves = {
        "CL": pd.DataFrame(
            {
                "F1": cl_f1,
                "F2": cl_f1 * (1 + basis),
                "F3": cl_f1 * (1 + 1.5 * basis),
            },
            index=idx,
        ),
        "XB": pd.DataFrame(
            {"F1": xb_f1, "F2": xb_f1 + 0.01},
            index=idx,
        ),
        "HO": pd.DataFrame(
            {"F1": ho_f1, "F2": ho_f1 + 0.01},
            index=idx,
        ),
        "CO": pd.DataFrame(
            {"F1": cl_f1 + 2, "F2": (cl_f1 + 2) * (1 + basis * 0.8)},
            index=idx,
        ),
        "QS": pd.DataFrame(
            {"F1": (cl_f1 + 10) * 7.45, "F2": (cl_f1 + 11) * 7.45},
            index=idx,
        ),
    }
    for df in curves.values():
        df.index.name = "date"

    # weekly-ish inventory
    inv_level = 400 + 40 * np.sin(np.linspace(0, 20, n)) + rng.normal(0, 5, n)
    inventory = pd.DataFrame(
        {"CL": inv_level, "XB": inv_level * 0.5, "HO": inv_level * 0.3},
        index=idx,
    )
    inventory.index.name = "date"

    iv = pd.DataFrame(
        {
            "CL": 25 + 10 * np.abs(np.sin(np.linspace(0, 15, n))) + rng.normal(0, 1, n),
            "CO": 24 + 9 * np.abs(np.sin(np.linspace(0, 15, n))) + rng.normal(0, 1, n),
            "XB": 28 + rng.normal(0, 1.5, n),
            "HO": 27 + rng.normal(0, 1.5, n),
            "QS": 26 + rng.normal(0, 1.5, n),
        },
        index=idx,
    )
    iv.index.name = "date"
    return {"curves": curves, "inventory": inventory, "iv": iv}
