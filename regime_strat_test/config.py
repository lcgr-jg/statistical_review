"""
Central configuration for regime-conditional commodity backtests.

Universe: US (CL/XB/HO) + ICE (CO/QS). Sample start for curve/inventory
strategies can go earlier; vol strategies are capped by listed IV history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "data" / "cache"

# Curve / inventory history can go further back than listed energy IV.
CURVE_START = datetime(2010, 1, 1)
VOL_START = datetime(2015, 1, 1)  # practical floor for CL/CO ATM IV continuity
DEFAULT_END = datetime.today()

# Bloomberg generic front months (continuous). Spread P&L uses stacked generics;
# roll bias is accepted in v1; contract-month reconstruction is a later upgrade.
US_CURVE = {
    "CL": [f"CL{i} Comdty" for i in range(1, 13)],
    "XB": [f"XB{i} Comdty" for i in range(1, 7)],
    "HO": [f"HO{i} Comdty" for i in range(1, 7)],
}
ICE_CURVE = {
    "CO": [f"CO{i} Comdty" for i in range(1, 13)],
    "QS": [f"QS{i} Comdty" for i in range(1, 7)],
}

# Approximate ATM IV tickers (generic). Override in config if your desk uses
# different Bloomberg vol securities (e.g. implied vol indexes / OTC marks).
ATM_IV_TICKERS = {
    "CL": "CL1 Comdty",  # field HIST_CALL_IMP_VOL / IVOL_MID via overrides
    "CO": "CO1 Comdty",
    "XB": "XB1 Comdty",
    "HO": "HO1 Comdty",
    "QS": "QS1 Comdty",
}

# EIA / weekly stocks (Bloomberg indexes).
# NOTE: many desktop licenses do not return these over API — validate with
# `python validate_symbology.py`. If empty, drop a CSV into data/manual_inventory/
# (columns: date, CL, XB, HO) or look up tickers via EIA <GO> on the terminal.
INVENTORY_TICKERS = {
    "CL": "DOEUSCR Index",   # US crude excluding SPR (common; may need entitlement)
    "XB": "DOEUSGSL Index",  # total motor gasoline
    "HO": "DOEUSDSL Index",  # distillate fuel oil
}
MANUAL_INVENTORY_CSV = ROOT / "data" / "manual_inventory" / "eia_stocks.csv"

PRICE_FIELD = "PX_LAST"
IV_FIELD = "HIST_CALL_IMP_VOL"  # fallback handled in data.vols

# Half-spread cost model: charged once on entry and once on exit per leg.
# Units are in price points of the underlying future.
HALF_SPREAD = {
    "CL": 0.005,   # $0.01 full bid-ask → half = 0.005
    "CO": 0.005,
    "XB": 0.0005,
    "HO": 0.0005,
    "QS": 0.25,    # gasoil often quoted in $/mt; tune to your marks
}

CONTRACT_MULTIPLIER = {
    "CL": 1000,
    "CO": 1000,
    "XB": 42000,
    "HO": 42000,
    "QS": 100,
}


class HoldingMode(str, Enum):
    FIXED_DAYS = "fixed_days"
    WEEKLY = "weekly"
    REGIME_EXIT = "regime_exit"


@dataclass
class HoldingConfig:
    """Flexible holding / rebalance convention."""
    mode: HoldingMode = HoldingMode.FIXED_DAYS
    hold_days: int = 20
    # For REGIME_EXIT: flatten when continuous regime signal crosses this level
    # toward the "inactive" side (strategy-specific interpretation).
    exit_regime_threshold: float | None = None


@dataclass
class WalkForwardConfig:
    train_years: int = 3
    test_years: int = 1
    step_years: int = 1
    min_train_obs: int = 60  # daily regime obs; trade-blotter fits use a lower floor
    n_buckets: int = 5


@dataclass
class BacktestConfig:
    complex: Literal["US", "ICE", "BOTH"] = "BOTH"
    start: datetime = CURVE_START
    end: datetime = field(default_factory=lambda: DEFAULT_END)
    vol_start: datetime = VOL_START
    holding: HoldingConfig = field(default_factory=HoldingConfig)
    walk_forward: WalkForwardConfig = field(default_factory=WalkForwardConfig)
    use_cache: bool = True
    refresh_cache: bool = False
    on_server: bool = False  # True → BPIPE server auth in bloomberg.bpipe
    annualization: int = 252


# Labeled stress windows for event panels (inclusive).
STRESS_WINDOWS = {
    "oil_crash_2014_15": (datetime(2014, 6, 1), datetime(2015, 12, 31)),
    "covid_crash_2020": (datetime(2020, 2, 15), datetime(2020, 4, 30)),
    "wti_negative_apr2020": (datetime(2020, 4, 1), datetime(2020, 5, 15)),
    "russia_ukraine_2022": (datetime(2022, 2, 15), datetime(2022, 6, 30)),
    "banking_stress_2023": (datetime(2023, 3, 1), datetime(2023, 5, 15)),
}
