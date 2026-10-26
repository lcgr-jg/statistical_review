# Run latam_vol_rv_backtest.py first (writes rv_out_3M_2_21.pkl), then this script.
import numpy as np, pandas as pd, matplotlib.pyplot as plt, latam_vol_rv_backtest as B
o=pd.read_pickle('rv_out_3M_2_21.pkl'); R=o['R']; c=o['curves']; books=o['books']
short={"Ex-ante VRP (IV - trailing RV, vol pts)":"Ex-ante VRP","IV / trailing RV ratio":"IV/RV ratio",
 "IV percentile vs own realized history":"IV pct vs own history","Historical VRP % (structural richness)":"Historical VRP",
 "IV z-score vs own 1y implied":"IV z-score (1y)","Short-all basket (benchmark)":"Short-all basket"}
col={"Ex-ante VRP":"#1f77b4","IV/RV ratio":"#17becf","IV pct vs own history":"#d62728","Historical VRP":"#7f7f7f","IV z-score (1y)":"#ff7f0e","Short-all basket":"k"}
fig=plt.figure(figsize=(16,15)); gs=fig.add_gridspec(3,2,hspace=.38,wspace=.22)
ax=fig.add_subplot(gs[0,:])
for k,d in c.items():
    n=short[k]; ax.plot(d.sum(axis=1).cumsum(),color=col[n],lw=2.4 if n in("IV pct vs own history","Short-all basket") else 1.3,ls='--' if n=="Short-all basket" else '-',label=n)
for y in ["2015-01-01","2020-01-01"]: pass
ax.axvspan(pd.Timestamp("2020-02-15"),pd.Timestamp("2020-06-30"),color='grey',alpha=.15)
ax.axhline(0,color='k',lw=.7); ax.grid(ls='--',alpha=.5); ax.legend(ncol=3,fontsize=9,loc='lower left')
ax.set_title("Cumulative net P&L, 3M vega-neutral long/short (short 2 richest, long 2 cheapest), monthly cohorts, daily MTM, 1x illustrative costs")
ax.set_ylabel("vol pts × vega units")
# sharpe bars
ax=fig.add_subplot(gs[1,0]); names=list(short); x=np.arange(len(names))
for j,(cx,a) in enumerate([(0,.35),(1,1)]):
    v=[R.loc[(k,cx),'sharpe'] for k in names]; t=[R.loc[(k,cx),'t_nw'] for k in names]
    bars=ax.bar(x+(j-.5)*.38,v,.38,color=[col[short[k]] for k in names],alpha=a,label="gross" if cx==0 else "net of 1x costs")
    for xi,vi,ti in zip(x+(j-.5)*.38,v,t): ax.text(xi,vi+(.03 if vi>=0 else -.09),f"t={ti:.1f}",ha='center',fontsize=7.5)
ax.set_xticks(x,[short[k] for k in names],rotation=20,fontsize=8.5); ax.axhline(0,color='k',lw=.7); ax.grid(axis='y',ls='--',alpha=.5)
ax.set_title("Annualized Sharpe (monthly MTM P&L), Newey-West t-stats\nfaded = before costs, solid = after 1x costs",fontsize=10); ax.legend(fontsize=8)
# by year for percentile and basket
ax=fig.add_subplot(gs[1,1]); p=c["IV percentile vs own realized history"].sum(axis=1); b=c["Short-all basket (benchmark)"].sum(axis=1)
py=p.groupby(p.index.year).sum(); by=b.groupby(b.index.year).sum(); yx=np.arange(len(py))
ax.bar(yx-.2,py,.4,color='#d62728',label="IV pct L/S (net)"); ax.bar(yx+.2,by,.4,color='k',alpha=.6,label="Short-all basket (net)")
ax.set_xticks(yx,py.index,rotation=45); ax.axhline(0,color='k',lw=.7); ax.grid(axis='y',ls='--',alpha=.5); ax.legend(fontsize=8)
ax.set_title("P&L by year: the RV signal pays in crises, the short basket pays in calm",fontsize=10)
# positions heatmap
ax=fig.add_subplot(gs[2,0]); bk=books["IV percentile vs own realized history"]
W=pd.DataFrame([w for _,w in bk],index=[t for t,_ in bk],columns=B.PAIRS)
ax.imshow(W.T.values,aspect='auto',cmap='RdBu',vmin=-.6,vmax=.6,interpolation='nearest')
ax.set_yticks(range(5),[f"USD{k}" for k in B.PAIRS]); tk=np.arange(0,len(W),12); ax.set_xticks(tk,[W.index[i].year for i in tk])
ax.set_title("IV pct signal positioning at each entry (blue = long vega, red = short vega)",fontsize=10)
# combination
ax=fig.add_subplot(gs[2,1])
for lam,cl,lab in [(0,'k',"Short basket alone"),(0.5,'#9467bd',"Short basket + 0.5× IV-pct L/S overlay")]:
    ax.plot((b+lam*p).cumsum(),color=cl,lw=1.8,label=lab)
ax.axhline(0,color='k',lw=.7); ax.grid(ls='--',alpha=.5); ax.legend(fontsize=8,loc='upper left')
ax.set_title("Hypothesis only (chosen in-sample): RV overlay as a crisis hedge for short vol\nSharpe 0.28 → 0.55, worst month −24.6 → −14.6",fontsize=10)
fig.suptitle("LatAm FX vol relative value: 3M, 2015 – Oct 2026",fontsize=14,y=.93)
plt.savefig("latam_vol_rv_backtest.png",dpi=125,bbox_inches='tight')
