"""LatAm FX vol cones + volatility risk premium. Input: latam_fx.xlsx (one Bloomberg sheet per pair)."""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
x = pd.read_excel("latam_fx.xlsx", sheet_name=None, header=None)
D = {}
for k, raw in x.items():
    df = raw.iloc[8:, 1:13].copy(); df.columns = ["date"] + raw.iloc[5, 2:13].tolist()
    df["date"] = pd.to_datetime(df["date"]); D[k] = df.set_index("date").apply(pd.to_numeric, errors="coerce")
M = {"3M":3,"6M":6,"9M":9,"1Y":12}; TD = {"3M":63,"6M":126,"9M":189,"1Y":252}
def prep(k):
    df = D[k]; spot = df[f"USD{k} Curncy"]; spot = spot[spot.diff()!=0]
    ret = np.log(spot).diff().dropna(); return df, spot, ret
def rv_between(ret, starts, ends):
    idx = ret.index; c = np.concatenate([[0], np.cumsum(ret.values**2)])
    a = idx.searchsorted(starts, side='right'); b = idx.searchsorted(ends, side='right')
    n = b - a; return np.sqrt((c[b]-c[a])/np.maximum(n,1)*252)*100, n
R = {}
for k in D:
    df, spot, ret = prep(k); dates = spot.index; last = dates[-1]
    out, trail = {}, {}
    for t,m in M.items():
        iv = df[f"USD{k}V{t} BGN Curncy"].reindex(dates)
        ends = dates + pd.DateOffset(months=m); ok = ends <= last
        rv, n = rv_between(ret, dates[ok], ends[ok])
        out[t] = pd.DataFrame({"iv": iv[ok].values, "rv": rv}, index=dates[ok])
        st = dates - pd.DateOffset(months=m); ok2 = st >= dates[0]
        trv, _ = rv_between(ret, st[ok2], dates[ok2]); trail[t] = pd.Series(trv, index=dates[ok2])
    R[k] = dict(df=df, spot=spot, ret=ret, out=out, trail=trail)

def sharpe(x, m):
    idx=x.index; v=(x.iv-x.rv).values; vv=((x.iv**2-x.rv**2)/(2*x.iv)).values; a=[];b=[]
    for t0 in idx[idx<idx[0]+pd.DateOffset(months=m)]:
        seq=[];t=t0
        while (i:=idx.searchsorted(t))<len(idx): seq.append(i); t=idx[i]+pd.DateOffset(months=m)
        s=v[seq]; ss=vv[seq]; a.append(s.mean()/s.std(ddof=1)*np.sqrt(12/m)); b.append(ss.mean()/ss.std(ddof=1)*np.sqrt(12/m))
    return np.mean(a), np.mean(b)
rows=[]
for k,r in R.items():
    for t,m in M.items():
        x=r["out"][t]; v=x.iv-x.rv; p=x[x.index>='2016-01-01']
        sv, svar = sharpe(x,m); sv16, svar16 = sharpe(p,m)
        # cone percentile of current IV & current trailing realized
        n=TD[t]; rvdist=r["ret"].rolling(n).std().dropna()*np.sqrt(252)*100
        iv_now=r["df"][f"USD{k}V{t} BGN Curncy"].iloc[-1]
        rows.append(dict(pair=k,tenor=t,mean=v.mean(),median=v.median(),hit=(v>0).mean()*100,worst=v.min(),
            mean16=(p.iv-p.rv).mean(), sh_vol=sv, sh_var=svar, sh_vol16=sv16, sh_var16=svar16,
            ann_pnl=v.mean()*12/m, iv_now=iv_now, iv_pct=(rvdist<iv_now).mean()*100,
            rv_mean=rvdist.mean(), trail_now=r["trail"][t].iloc[-1], exante_now=iv_now-r["trail"][t].iloc[-1]))
M={"3M":3,"6M":6,"9M":9,"1Y":12}; TD={"3M":63,"6M":126,"9M":189,"1Y":252}
PAIRS=list(R); MAXN=260
S = pd.DataFrame(rows)

# ---- cones
fig,axs=plt.subplots(2,3,figsize=(17,10)); axs=axs.ravel()
for ax,k in zip(axs,PAIRS):
    r=R[k]; rows=[]
    for n in range(5,MAXN+1):
        rv=r["ret"].rolling(n).std().dropna()*np.sqrt(252)*100
        rows.append((n,rv.max(),rv.min(),rv.mean(),rv.std(),rv.iloc[-1]))
    c=pd.DataFrame(rows,columns=["n","hi","lo","mean","std","cur"]).set_index("n")
    ax.plot(c.index,c.hi,'k',lw=1.3,label="Hi/Low"); ax.plot(c.index,c.lo,'k',lw=1.3)
    ax.plot(c.index,c["mean"]+2*c["std"],color='darkorange',lw=1.3,label="±2 std")
    ax.plot(c.index,(c["mean"]-2*c["std"]).clip(lower=0),color='darkorange',lw=1.3)
    ax.plot(c.index,c["mean"]+c["std"],'r',lw=1.3,label="±1 std"); ax.plot(c.index,c["mean"]-c["std"],'r',lw=1.3)
    ax.plot(c.index,c["mean"],'b',lw=1.3,label="Mean"); ax.plot(c.index,c.cur,color='grey',ls='--',lw=1.1,label="Current realized")
    for t,n in TD.items():
        row=S[(S.pair==k)&(S.tenor==t)].iloc[0]
        ax.scatter(n,row.iv_now,s=55,color='red',edgecolor='darkred',zorder=5)
        ax.annotate(f"{row.iv_now:.1f}\n{row.iv_pct:.0f}p",(n,row.iv_now),xytext=(5,6),textcoords='offset points',fontsize=7.5)
    ax.set_title(f"USD{k}"); ax.set_xlim(0,MAXN); ax.set_ylim(0,min(c.hi.max()*1.05,45)); ax.grid(ls='--',alpha=.5)
    ax.set_xlabel("window / days to expiry (trading days)"); ax.set_ylabel("vol %")
axs[0].scatter([],[],color='red',edgecolor='darkred',label="ATM implied (pct of realized)")
axs[0].legend(fontsize=8,loc='upper right')
# summary panel: current IV vs mean realized at 3M
ax=axs[5]; s3=S[S.tenor=="3M"].set_index("pair"); x=np.arange(len(PAIRS))
ax.bar(x-.27,s3.rv_mean,.27,color='lightsteelblue',label="Mean 3M realized (history)")
ax.bar(x,s3.trail_now,.27,color='grey',label="Trailing 3M realized now")
ax.bar(x+.27,s3.iv_now,.27,color='red',label="3M ATM implied now")
ax.set_xticks(x,PAIRS); ax.set_title("3M snapshot, 26 Oct 2026"); ax.legend(fontsize=8); ax.grid(axis='y',ls='--',alpha=.5); ax.set_ylabel("vol %")
fig.suptitle("LatAm FX volatility cones, Jan 2014 – 26 Oct 2026 (y-axis capped at 45%)",fontsize=13)
plt.tight_layout(); plt.savefig("latam_vol_cones.png",dpi=130)

# ---- VRP
cols={"COP":"#d62728","MXN":"#2ca02c","BRL":"#ff7f0e","CLP":"#1f77b4","PEN":"#9467bd"}
fig=plt.figure(figsize=(17,15)); gs=fig.add_gridspec(4,6,height_ratios=[1,1,1.2,1.1],hspace=.45,wspace=.6)
for i,k in enumerate(PAIRS):
    ax=fig.add_subplot(gs[i//3 if i<3 else 1, (i%3)*2:(i%3)*2+2]) if i<3 else fig.add_subplot(gs[1,(i-3)*2:(i-3)*2+2])
    for t,ls in [("3M","-"),("1Y","--")]:
        x=R[k]["out"][t]; ax.plot(x.index,(x.iv-x.rv).rolling(63).mean(),color=cols[k],ls=ls,lw=1.3,label=t)
    ax.axhline(0,color='k',lw=.7); ax.set_title(f"USD{k}: ex-post VRP (3M rolling mean)",fontsize=10); ax.grid(ls='--',alpha=.5)
    ax.set_ylabel("vol pts"); ax.legend(fontsize=8,loc='lower right'); ax.set_ylim(-12,8)
ax=fig.add_subplot(gs[1,4:6])
for j,t in enumerate(["3M","1Y"]):
    v=[((R[k]["out"][t].iv-R[k]["out"][t].rv)/R[k]["out"][t].iv).mean()*100 for k in PAIRS]
    ax.bar(np.arange(5)+(j-.5)*.38,v,.38,color=[cols[k] for k in PAIRS],alpha=1 if t=="3M" else .45,label=t+(" (solid)" if t=="3M" else " (faded)"))
ax.set_xticks(range(5),PAIRS); ax.axhline(0,color='k',lw=.7); ax.grid(axis='y',ls='--',alpha=.5)
ax.set_title("Mean VRP as % of implied, full sample",fontsize=10); ax.set_ylabel("%"); ax.legend(fontsize=8)
s=S.pivot(index="pair",columns="tenor",values="sh_vol")[list(M)].loc[PAIRS]; s2=S.pivot(index="pair",columns="tenor",values="sh_vol16")[list(M)].loc[PAIRS]
# cumulative 3M ladder P&L
ax=fig.add_subplot(gs[2,:]); basket=[]
for k in PAIRS:
    x=R[k]["out"]["3M"]; npm=x.groupby(x.index.to_period('M')).size().mean()*3
    p=pd.Series(((x.iv-x.rv)/npm).values,index=x.index+pd.DateOffset(months=3)).sort_index()
    ax.plot(p.cumsum(),color=cols[k],lw=1.5,label=f"USD{k}"); basket.append(p.groupby(p.index).sum())
b=pd.concat(basket,axis=1,sort=True).fillna(0).mean(axis=1).cumsum(); ax.plot(b,color='k',lw=2.2,label="Equal-vega basket")
ax.axhline(0,color='k',lw=.7); ax.grid(ls='--',alpha=.5); ax.legend(ncol=6,fontsize=9,loc='upper left')
ax.set_title("Cumulative P&L: short 3M ATM vol laddered daily, 1 unit of vega outstanding (vol-pt basis, booked at expiry)"); ax.set_ylabel("vol pts × vega")
# heatmaps
for j,(mat,title) in enumerate([(s,"Sharpe, full sample (vol basis)"),(s2,"Sharpe, 2016 onward (vol basis)"),
        (S.pivot(index="pair",columns="tenor",values="sh_var")[list(M)].loc[PAIRS],"Sharpe, full sample (variance basis)")]):
    ax=fig.add_subplot(gs[3,j*2:j*2+2]); im=ax.imshow(mat.values,cmap='RdYlGn',vmin=-.6,vmax=.9,aspect='auto')
    ax.set_xticks(range(4),mat.columns); ax.set_yticks(range(len(PAIRS)),PAIRS); ax.set_title(title,fontsize=10)
    for a in range(mat.shape[0]):
        for bb in range(4): ax.text(bb,a,f"{mat.values[a,bb]:.2f}",ha='center',va='center',fontsize=9)
fig.suptitle("LatAm FX volatility risk premium: ATM implied minus subsequent realized",fontsize=13,y=.92)
plt.savefig("latam_vrp.png",dpi=130,bbox_inches='tight')
print(S.round(2).to_string())
