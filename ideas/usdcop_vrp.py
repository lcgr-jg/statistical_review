# USDCOP volatility risk premium by tenor. Step 1: compute; step 2: stats; step 3: chart.
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
raw = pd.read_excel("usdcop.xlsx", header=None)
df = raw.iloc[8:, 1:13].copy(); df.columns = ["date"] + raw.iloc[5, 2:13].tolist()
df["date"] = pd.to_datetime(df["date"]); df = df.set_index("date").apply(pd.to_numeric, errors="coerce")
spot = df["USDCOP Curncy"]; spot = spot[spot.diff() != 0]
ret = np.log(spot).diff().dropna()
TEN = {"3M": (3, "USDCOPV3M BGN Curncy"), "6M": (6, "USDCOPV6M BGN Curncy"),
       "9M": (9, "USDCOPV9M BGN Curncy"), "1Y": (12, "USDCOPV1Y BGN Curncy")}
dates = spot.index
r2 = ret**2; cs = r2.cumsum(); cnt = pd.Series(1, index=ret.index).cumsum()
out = {}
for k, (m, col) in TEN.items():
    iv = df[col].reindex(dates)
    rows = []
    for t in dates:
        end = t + pd.DateOffset(months=m)
        if end > dates[-1]: break
        w = ret[(ret.index > t) & (ret.index <= end)]
        rv = np.sqrt((w**2).mean() * 252) * 100  # zero-mean realized
        rows.append((t, iv[t], rv, len(w)))
    x = pd.DataFrame(rows, columns=["date", "iv", "rv", "n"]).set_index("date")
    # trailing realized over same tenor (signal, known at t)
    tr = []
    for t in x.index.union(dates):
        pass
    out[k] = x
# trailing realized
trail = {}
for k, (m, col) in TEN.items():
    vals = {}
    for t in dates:
        st = t - pd.DateOffset(months=m)
        if st < dates[0]: continue
        w = ret[(ret.index > st) & (ret.index <= t)]
        vals[t] = np.sqrt((w**2).mean() * 252) * 100
    trail[k] = pd.Series(vals)


M = {"3M":3,"6M":6,"9M":9,"1Y":12}
res=[]
for k,x in out.items():
    m=M[k]
    x=x.copy(); x["vrp"]=x.iv-x.rv; x["vpnl"]=(x.iv**2-x.rv**2)/(2*x.iv)
    # non-overlapping sharpe averaged across start offsets
    idx=x.index; sh=[]; sh_v=[]; ann=[]
    offs=idx[idx< idx[0]+pd.DateOffset(months=m)]
    for t0 in offs:
        seq=[]; t=t0
        while True:
            i=idx.searchsorted(t)
            if i>=len(idx): break
            seq.append(idx[i]); t=idx[i]+pd.DateOffset(months=m)
        s=x.loc[seq]
        sh.append(s.vrp.mean()/s.vrp.std()*np.sqrt(12/m))
        sh_v.append(s.vpnl.mean()/s.vpnl.std()*np.sqrt(12/m))
        ann.append(len(seq))
    res.append(dict(tenor=k, obs=len(x), mean=x.vrp.mean(), median=x.vrp.median(),
        hit=(x.vrp>0).mean()*100, worst=x.vrp.min(), best=x.vrp.max(),
        vpnl_mean=x.vpnl.mean(), ann_vega_pnl=x.vpnl.mean()*12/m,
        sharpe_vol=np.mean(sh), sharpe_var=np.mean(sh_v), sh_min=np.min(sh_v), sh_max=np.max(sh_v),
        n_indep=np.mean(ann), worst_date=x.vrp.idxmin().date()))
r=pd.DataFrame(res).set_index("tenor"); pd.set_option('display.width',250)
print(r.round(2).T)
# by year (start year) mean vrp
by=pd.DataFrame({k:(x.iv-x.rv).groupby(x.index.year).mean() for k,x in out.items()})
print(by.round(2))
# trailing VRP current
for k in M: print(k, "IV",df[f"USDCOPV{k if k!='1Y' else '1Y'} BGN Curncy"].iloc[-1], "trail RV", round(trail[k].iloc[-1],2))
# signal: does iv - trailing rv predict ex-post vrp?
for k,x in out.items():
    s=(x.iv-trail[k].reindex(x.index)).dropna(); y=(x.iv-x.rv).reindex(s.index)
    q=pd.qcut(s,4,labels=["Q1 low","Q2","Q3","Q4 high"])
    print(k, "corr",round(s.corr(y),2), y.groupby(q,observed=True).mean().round(2).to_dict())

M={"3M":3,"6M":6,"9M":9,"1Y":12}
def sharpe(x,m):
    idx=x.index; v=x.iv-x.rv; vv=(x.iv**2-x.rv**2)/(2*x.iv); a=[];b=[]
    for t0 in idx[idx<idx[0]+pd.DateOffset(months=m)]:
        seq=[];t=t0
        while (i:=idx.searchsorted(t))<len(idx): seq.append(idx[i]); t=idx[i]+pd.DateOffset(months=m)
        a.append(v[seq].mean()/v[seq].std()*np.sqrt(12/m)); b.append(vv[seq].mean()/vv[seq].std()*np.sqrt(12/m))
    return np.mean(a),np.mean(b)
for k,x in out.items():
    print(k,"post2016 sharpe",np.round(sharpe(x[x.index>='2016-01-01'],M[k]),2))
cols={"3M":"#d62728","6M":"#ff7f0e","9M":"#2ca02c","1Y":"#1f77b4"}
fig,(a1,a2,a3)=plt.subplots(3,1,figsize=(13,12),sharex=True,gridspec_kw=dict(height_ratios=[1.2,1,1]))
for k,x in out.items():
    a1.plot(x.index,(x.iv-x.rv).rolling(63).mean(),color=cols[k],lw=1.4,label=k)
    tv=(df[f"USDCOPV{k} BGN Curncy"]-trail[k]).dropna()
    a2.plot(tv.index,tv.rolling(21).mean(),color=cols[k],lw=1.2,label=k)
    # ladder P&L: sell 1/N of the vega each day, P&L per unit total vega, booked at expiry -> annual-equivalent cumulative
    m=M[k]; n_per=x.groupby(x.index.to_period('M')).size().mean()*m
    pnl=(x.iv-x.rv)/n_per
    exp=x.index.map(lambda t:t+pd.DateOffset(months=m))
    a3.plot(pd.Series(pnl.values,index=exp).sort_index().cumsum(),color=cols[k],lw=1.6,label=k)
a1.axhline(0,color='k',lw=.8); a2.axhline(0,color='k',lw=.8); a3.axhline(0,color='k',lw=.8)
a1.set_title("Ex-post VRP: implied at t minus realized over the following tenor (3M rolling mean, plotted at trade date)")
a1.set_ylabel("vol pts")
a2.set_title("Ex-ante VRP: implied minus trailing realized over same tenor (1M rolling mean) — known at t")
a2.set_ylabel("vol pts")
a3.set_title("Cumulative P&L, short ATM vol laddered daily, 1 unit of vega outstanding per tenor (vol-pt basis, booked at expiry)")
a3.set_ylabel("vol pts × vega")
for a in (a1,a2,a3): a.grid(ls='--',alpha=.5); a.legend(ncol=4,loc='upper left',fontsize=9)
plt.tight_layout(); plt.savefig("usdcop_vrp.png",dpi=140)
