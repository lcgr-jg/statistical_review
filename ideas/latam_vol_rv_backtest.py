"""
LatAm FX vol relative-value backtest.

Each month, open a 3M position in every pair: short vega in the "richest" pairs,
long vega in the "cheapest", vega-neutral. Positions are marked daily as vol
swaps and held to expiry; bid/offer is charged at entry.

Daily mark (per unit of vega, long-vol sign), for a trade struck at K over T days:
    V_t = (e/T) * (RV_elapsed - K) + ((T - e)/T) * (IV3M_t - K)
At entry V = 0; at expiry V = RV - K. Daily P&L = change in V.
Approximations: constant-maturity 3M implied stands in for the remaining-life
implied; vol-swap (not straddle) payoff; delta-hedging costs ignored.
"""
import os, numpy as np, pandas as pd

FILE = "latam_fx.xlsx"
PAIRS = ["COP", "MXN", "BRL", "CLP", "PEN"]
TENOR = os.environ.get("TENOR", "3M"); MONTHS = {"3M": 3, "6M": 6, "1Y": 12}[TENOR]
START = "2015-01-01"          # first entry; 2014 is warm-up for the signals
REBAL_EVERY = int(os.environ.get("REBAL", 21))              # trading days between cohorts (~monthly)
N_SIDE = int(os.environ.get("N_SIDE", 2))                    # pairs shorted / bought per cohort
# ILLUSTRATIVE half bid/offer in vol points (replace with dealer quotes)
HALF_SPREAD = {"MXN": 0.15, "BRL": 0.25, "CLP": 0.35, "COP": 0.40, "PEN": 0.50}

# ---------------- data on a common weekday calendar ----------------
raw = pd.read_excel(FILE, sheet_name=None, header=None)
spot, iv = {}, {}
for k in PAIRS:
    r = raw[k]; df = r.iloc[8:, 1:13].copy(); df.columns = ["date"] + r.iloc[5, 2:13].tolist()
    df["date"] = pd.to_datetime(df["date"]); df = df.set_index("date").apply(pd.to_numeric, errors="coerce")
    spot[k] = df[f"USD{k} Curncy"]; iv[k] = df[f"USD{k}V{TENOR} BGN Curncy"]
spot = pd.DataFrame(spot).ffill(); iv = pd.DataFrame(iv).ffill()
dates = spot.index; N = len(dates)
ret = np.log(spot).diff().fillna(0.0)
live = (ret != 0).astype(float)          # zero-change days = local holidays, excluded from day count
c_r2 = np.vstack([np.zeros(len(PAIRS)), np.cumsum(ret.values**2, axis=0)])   # c[i] = sum of r^2 over rows < i
c_n = np.vstack([np.zeros(len(PAIRS)), np.cumsum(live.values, axis=0)])

def rv(i0, i1):
    """annualized zero-mean realized vol over returns in rows i0+1..i1 (all pairs)"""
    n = c_n[i1 + 1] - c_n[i0 + 1]
    return np.sqrt((c_r2[i1 + 1] - c_r2[i0 + 1]) / np.maximum(n, 1) * 252) * 100

expiry = np.array([dates.searchsorted(d + pd.DateOffset(months=MONTHS)) for d in dates])
expiry = np.where(expiry >= N, -1, expiry)

# trailing 3M realized and ex-post realized for every date
trail = np.full((N, len(PAIRS)), np.nan); expost = np.full((N, len(PAIRS)), np.nan)
for i, d in enumerate(dates):
    s = dates.searchsorted(d - pd.DateOffset(months=MONTHS))
    if dates[0] <= d - pd.DateOffset(months=MONTHS): trail[i] = rv(s, i)
    if expiry[i] > 0: expost[i] = rv(i, expiry[i])
trail = pd.DataFrame(trail, index=dates, columns=PAIRS)
expost = pd.DataFrame(expost, index=dates, columns=PAIRS)
rv63 = ret.pow(2).rolling(63).sum().div(live.rolling(63).sum()).mul(252).pow(.5).mul(100)

# ---------------- signals (higher = richer = sell), all known at t ----------------
def signals():
    S = {}
    S["Ex-ante VRP (IV - trailing RV, vol pts)"] = iv - trail
    S["IV / trailing RV ratio"] = iv / trail
    # where today's IV sits in the pair's own realized-vol history (expanding, no look-ahead)
    pct = pd.DataFrame(index=dates, columns=PAIRS, dtype=float)
    for k in PAIRS:
        h = rv63[k].values; v = iv[k].values
        for i in range(N):
            past = h[:i + 1]; past = past[~np.isnan(past)]
            if len(past) >= 250: pct.iloc[i, PAIRS.index(k)] = (past < v[i]).mean()
    S["IV percentile vs own realized history"] = pct
    # pair's historical VRP in % of IV, using only trades that had expired by t
    hist = pd.DataFrame(index=dates, columns=PAIRS, dtype=float)
    vrp_pct = (iv - expost) / iv
    for i in range(N):
        matured = expiry[:i + 1]; ok = (matured >= 0) & (matured <= i)
        if ok.sum() >= 120: hist.iloc[i] = vrp_pct.iloc[:i + 1][ok].mean().values
    S["Historical VRP % (structural richness)"] = hist
    S["IV z-score vs own 1y implied"] = (iv - iv.rolling(252).mean()) / iv.rolling(252).std()
    return S

# ---------------- engine ----------------
def run(weights_fn, cost_mult=1.0):
    pnl = np.zeros((N, len(PAIRS))); cost = np.zeros((N, len(PAIRS))); book = []
    entries = [i for i in range(dates.searchsorted(pd.Timestamp(START)), N, REBAL_EVERY) if expiry[i] > 0]
    for i in entries:
        w = weights_fn(i)
        if w is None: continue
        j = expiry[i]; K = iv.values[i]; T = c_n[j + 1] - c_n[i + 1]
        V_prev = np.zeros(len(PAIRS))
        for d in range(i + 1, j + 1):
            e = c_n[d + 1] - c_n[i + 1]; f = e / T
            V = f * (rv(i, d) - K) + (1 - f) * (iv.values[d] - K) if d < j else rv(i, j) - K
            pnl[d] += w * (V - V_prev); V_prev = V
        cost[i] -= np.abs(w) * np.array([HALF_SPREAD[k] for k in PAIRS]) * cost_mult
        book.append((dates[i], w))
    daily = pd.DataFrame(pnl + cost, index=dates, columns=PAIRS)
    return daily.loc[START:], book

def ls_weights(sig):
    def f(i):
        s = sig.iloc[i]
        if s.isna().any(): return None
        rk = s.rank().values; w = np.zeros(len(PAIRS))
        w[rk > len(PAIRS) - N_SIDE] = -1.0 / N_SIDE      # richest: sell vega
        w[rk <= N_SIDE] = +1.0 / N_SIDE                  # cheapest: buy vega
        return w
    return f

def basket(i): return np.full(len(PAIRS), -1.0 / len(PAIRS))

def nw_t(x, lags=3):
    x = np.asarray(x) - np.mean(x); n = len(x); g0 = x @ x / n; s = g0
    for L in range(1, lags + 1): s += 2 * (1 - L / (lags + 1)) * (x[L:] @ x[:-L]) / n
    return np.mean(np.asarray(x) + 0) , np.sqrt(s / n)

def stats(daily, ref=None):
    p = daily.sum(axis=1); m = p.resample("ME").sum(); yrs = len(m) / 12
    mu = m.mean(); se = nw_t(m.values)[1]
    eq = p.cumsum(); dd = (eq - eq.cummax()).min()
    out = dict(ann_pnl=mu * 12, sharpe=mu / m.std() * np.sqrt(12), t_nw=mu / se, hit_m=(m > 0).mean() * 100,
               max_dd=dd, worst_m=m.min(), years=yrs)
    if ref is not None:
        rm = ref.sum(axis=1).resample("ME").sum(); out["corr_to_short_basket"] = m.corr(rm)
        out["beta_to_short_basket"] = np.cov(m, rm)[0, 1] / rm.var()
    return out

if __name__ == "__main__":
    S = signals()
    pd.to_pickle(dict(S=S, iv=iv, trail=trail), f"sig_{TENOR}.pkl")
    base, _ = run(basket)
    rows, curves, books = [], {}, {}
    for name, sig in S.items():
        for cm in [0, 1, 2]:
            d, book = run(ls_weights(sig), cm)
            st = stats(d, base); st.update(signal=name, cost_x=cm); rows.append(st)
            if cm == 1: curves[name] = d; books[name] = book
    for cm in [0, 1, 2]:
        d, _ = run(basket, cm); st = stats(d); st.update(signal="Short-all basket (benchmark)", cost_x=cm); rows.append(st)
        if cm == 1: curves["Short-all basket (benchmark)"] = d
    R = pd.DataFrame(rows).set_index(["signal", "cost_x"])
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
    print(R.round(2))
    pd.to_pickle(dict(R=R, curves=curves, books=books), f"rv_out_{TENOR}_{N_SIDE}_{REBAL_EVERY}.pkl")
