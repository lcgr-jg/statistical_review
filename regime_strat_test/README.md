# Regime-conditional commodity backtests

Backtesting framework for oil / refined-products derivative strategies, each conditioned on a regime variable. Uses the existing Bloomberg BPIPE wrapper in `bloomberg/`, with **parquet caching** so walks and multi-strategy runs do not re-hit the API every time.

## Choices locked for v1

| Item | Choice |
|------|--------|
| Universe | US (`CL`/`XB`/`HO`) + ICE (`CO`/`QS`) |
| Data | Cache-first parquet under `data/cache/` |
| GEX / vanna / charm | Deferred to v2 (`gex_fade` stub) |
| Holding | Flexible: `fixed_days` / `weekly` / `regime_exit` |
| Costs | Half-spread per leg, entry + exit |
| History | Curves/inventory from ~2010; vol strategies from `VOL_START` (default 2015) |

## Strategies

1. **cash_and_carry** — long near / short deferred when contango % is rich  
2. **calendar_spread** — long front−back when inventory z is low  
3. **crack_mr** — fade 3-2-1 (US) or Brent–gasoil (ICE) when half-life is tradeable  
4. **vol_calendar** — sell rich near IV vs back-month proxy (IV %ile / RV–IV)  
5. **gex_fade** — stub only (v2)  
6. **seasonal_inventory** — long calendar when stocks tight but curve still contango  
7. **crack_skew** — RBOB vs HO relative-value mean reversion  

For each run the engine reports:

- Unconditional P&L metrics (Sharpe, hit rate, avg P&L)  
- Same metrics **bucketed by regime state at entry**  
- OLS of `pnl_net ~ regime_value` (linear + quadratic; flags threshold-like nonlinearity)  
- **Walk-forward** threshold re-estimation (train quantiles → test buckets)  
- **Stress panels**: 2014–15 crash, COVID, Apr-2020 WTI neg, 2022 RU/UA, 2023 banking  

## Setup

```bash
cd regime_strat_test
pip install -r requirements.txt
# blpapi from Bloomberg matching your license
```

## Cookbook notebook (mental models)

Open `notebooks/regime_cookbook.ipynb` — strategy cards, when/why edges work,
stress scar tissue, and a live desk checklist. Set `USE_LIVE = True` after cache exists.

```bash
# Validate Bloomberg tickers first
python validate_symbology.py
python validate_symbology.py --on-server
```

## Run

```bash
# Offline smoke test (no Bloomberg)
python run_backtest.py --demo

# Cached Bloomberg (first run pulls + writes parquet)
python run_backtest.py --complex BOTH --on-server

# Refresh cache
python run_backtest.py --refresh-cache --on-server

# Holding modes
python run_backtest.py --holding fixed_days --hold-days 20 --demo
python run_backtest.py --holding weekly --demo
python run_backtest.py --holding regime_exit --demo

# Subset of strategies
python run_backtest.py --demo --strategies cash_and_carry,crack_mr
```

Outputs land in `output/` (`*_trades.csv`, `*_buckets.csv`, `*_walkforward.csv`, `*_stress.csv`).

## Config knobs

Edit `config.py`:

- `US_CURVE` / `ICE_CURVE` / `INVENTORY_TICKERS` / `ATM_IV_TICKERS`  
- `HALF_SPREAD`, `VOL_START`, `STRESS_WINDOWS`  
- `IV_FIELD` if your Bloomberg vol field differs (`HIST_CALL_IMP_VOL` vs `IVOL_MID`, etc.)

## Design notes / caveats

- Generics (`CL1`…`CL12`) are used in v1; true contract-month reconstruction is a later upgrade (matters for carry purity).  
- Vol calendar P&L is a **vol-point structure proxy**, not full option revaluation.  
- Contango cash-and-carry here is futures-only (curve flatten bet in rich contango), not a financed physical storage arb.  
- Confirm EIA / IV Bloomberg tickers against your terminal symbology before trusting live results.

## Suggested next steps

1. Point tickers/fields at your desk’s Bloomberg conventions; first cached pull.  
2. Sanity-check one product curve + inventory plot.  
3. Run US crack + CL calendar with walk-forward.  
4. v2: dealer GEX feed + proper multi-tenor IV surface.
