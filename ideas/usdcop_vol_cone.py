"""
USDCOP volatility cone with current ATM implied vols overlaid.

Cone: for each window length N (trading days), compute annualized realized vol
over every rolling N-day window in the history, then plot Hi / Low / Mean /
Mean +/- 1 and 2 std across those windows. Implied vols are plotted as dots at
their tenor in trading days.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FILE = "usdcop.xlsx"
MAX_N = 260            # longest window (trading days)
ANN = 252              # annualization factor
DROP_HOLIDAYS = True   # drop zero-change days (Bloomberg fills holidays on a weekday calendar)
USE_PERCENTILES = False  # True -> 5/25/50/75/95 bands instead of mean +/- std
TENOR_DAYS = {"3M": 63, "6M": 126, "9M": 189, "1Y": 252}


# ---------- load Bloomberg export ----------
raw = pd.read_excel(FILE, header=None)
tickers = raw.iloc[5, 2:13].tolist()
df = raw.iloc[8:, 1:13].copy()
df.columns = ["date"] + tickers
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date").apply(pd.to_numeric, errors="coerce").dropna(how="all")

spot = df["USDCOP Curncy"]
if DROP_HOLIDAYS:
    spot = spot[spot.diff() != 0]          # removes forward-filled holidays
ret = np.log(spot).diff().dropna()

SKEW = {
    "25d RR": {"3M": "USDCOP25R3M BGN Curncy", "6M": "USDCOP25R6M BGN Curncy", "1Y": "USDCOP25R1y BGN Curncy"},
    "15d BF": {"3M": "USDCOP15B3M BGN Curncy", "6M": "USDCOP15B6M BGN Curncy", "1Y": "USDCOP15B1Y BGN Curncy"},
}

atm = {
    "3M": df["USDCOPV3M BGN Curncy"].iloc[-1],
    "6M": df["USDCOPV6M BGN Curncy"].iloc[-1],
    "9M": df["USDCOPV9M BGN Curncy"].iloc[-1],
    "1Y": df["USDCOPV1Y BGN Curncy"].iloc[-1],
}


# ---------- build the cone ----------
windows = np.arange(2, MAX_N + 1)
rows = []
for n in windows:
    rv = ret.rolling(n).std(ddof=1).dropna() * np.sqrt(ANN) * 100
    rows.append({
        "N": n,
        "hi": rv.max(), "lo": rv.min(), "mean": rv.mean(), "std": rv.std(),
        "p05": rv.quantile(.05), "p25": rv.quantile(.25), "p50": rv.median(),
        "p75": rv.quantile(.75), "p95": rv.quantile(.95),
        "current": rv.iloc[-1],
    })
cone = pd.DataFrame(rows).set_index("N")


# ---------- plot ----------
fig = plt.figure(figsize=(14, 10.5))
gs = fig.add_gridspec(2, 2, height_ratios=[1.6, 1], hspace=0.32, wspace=0.18)
ax = fig.add_subplot(gs[0, :])
x = cone.index

ax.plot(x, cone["hi"], color="black", lw=1.6, label="Hi")
if USE_PERCENTILES:
    ax.plot(x, cone["p95"], color="darkorange", lw=1.6, label="95th pct")
    ax.plot(x, cone["p75"], color="red", lw=1.6, label="75th pct")
    ax.plot(x, cone["p50"], color="blue", lw=1.6, label="Median")
    ax.plot(x, cone["p25"], color="red", lw=1.6, label="25th pct")
    ax.plot(x, cone["p05"], color="darkorange", lw=1.6, label="5th pct")
else:
    ax.plot(x, cone["mean"] + 2 * cone["std"], color="darkorange", lw=1.6, label="+2 std")
    ax.plot(x, cone["mean"] + cone["std"], color="red", lw=1.6, label="+1 std")
    ax.plot(x, cone["mean"], color="blue", lw=1.6, label="Mean")
    ax.plot(x, cone["mean"] - cone["std"], color="red", lw=1.6, label="-1 std")
    ax.plot(x, (cone["mean"] - 2 * cone["std"]).clip(lower=0), color="darkorange", lw=1.6, label="-2 std")
ax.plot(x, cone["lo"], color="black", lw=1.6, label="Low")
ax.plot(x, cone["current"], color="grey", lw=1.2, ls="--", label="Current realized (trailing N)")

for tenor, iv in atm.items():
    n = TENOR_DAYS[tenor]
    ax.scatter(n, iv, s=70, color="red", edgecolor="darkred", zorder=5)
    pct = (ret.rolling(n).std().dropna() * np.sqrt(ANN) * 100 < iv).mean() * 100
    ax.annotate(f"{tenor} ATM {iv:.2f}\n({pct:.0f}th pct)", (n, iv),
                textcoords="offset points", xytext=(8, 8), fontsize=8.5)
ax.scatter([], [], s=70, color="red", edgecolor="darkred", label="ATM implied vol")

ax.set_xlim(0, MAX_N)
ax.set_ylim(0, None)
ax.set_xlabel("WINDOW LENGTH / DAYS TO EXPIRATION (trading days)")
ax.set_ylabel("VOLATILITY (%)")
ax.set_title(f"USDCOP volatility cone  |  {spot.index[0]:%b %Y} – {spot.index[-1]:%d %b %Y}")
ax.grid(True, ls="--", alpha=0.6)
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=True, fontsize=9)


# ---------- skew panels: current RR / BF vs own history ----------
def skew_panel(ax, name, cols):
    tenors = list(cols)
    xs = np.arange(len(tenors))
    summary = []
    for i, t in enumerate(tenors):
        h = df[cols[t]].dropna()
        q = h.quantile([0, .05, .25, .5, .75, .95, 1]).values
        cur = h.iloc[-1]
        pct = (h < cur).mean() * 100
        z = (cur - h.mean()) / h.std()
        ax.vlines(i, q[0], q[6], color="black", lw=1)                         # min-max
        ax.vlines(i, q[1], q[5], color="darkorange", lw=6, alpha=.55)          # 5-95
        ax.vlines(i, q[2], q[4], color="red", lw=12, alpha=.55)                # 25-75
        ax.hlines(q[3], i - .12, i + .12, color="blue", lw=2)                  # median
        ax.scatter(i, cur, s=80, color="red", edgecolor="darkred", zorder=5)
        ax.annotate(f"{cur:.2f}\n{pct:.0f}th pct, z={z:+.1f}", (i, cur),
                    textcoords="offset points", xytext=(14, -6), fontsize=8.5)
        summary.append((name, t, cur, q[3], pct, z))
    ax.set_xticks(xs, tenors)
    ax.set_xlim(-.5, len(tenors) - .3)
    ax.set_ylabel("vol points")
    ax.set_title(f"{name}: current vs history")
    ax.grid(True, axis="y", ls="--", alpha=0.6)
    return summary

ax_rr = fig.add_subplot(gs[1, 0])
ax_bf = fig.add_subplot(gs[1, 1])
skew_rows = skew_panel(ax_rr, "25d RR", SKEW["25d RR"]) + skew_panel(ax_bf, "15d BF", SKEW["15d BF"])

from matplotlib.lines import Line2D
handles = [Line2D([], [], color="black", lw=1, label="Min–max"),
           Line2D([], [], color="darkorange", lw=6, alpha=.55, label="5th–95th pct"),
           Line2D([], [], color="red", lw=10, alpha=.55, label="25th–75th pct"),
           Line2D([], [], color="blue", lw=2, label="Median"),
           Line2D([], [], marker="o", ls="", color="red", markeredgecolor="darkred", ms=8, label="Current")]
ax_bf.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9)

plt.savefig("usdcop_vol_cone.png", dpi=150, bbox_inches="tight")
plt.show()

print(cone.loc[list(TENOR_DAYS.values()), ["lo", "mean", "std", "hi", "current"]].round(2))
print(pd.DataFrame(skew_rows, columns=["metric", "tenor", "current", "median", "pct", "z"]).round(2))
