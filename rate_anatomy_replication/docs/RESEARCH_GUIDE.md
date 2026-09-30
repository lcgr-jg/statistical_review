# Research and replication guide

**Primary target:** Beaudry, P., Cavallino, P., and Willems, T. (21 Sep 2026), “Anatomy of a rise: Monetary policy and the post-Covid surge in long-term interest rates,” VoxEU/CEPR.  
**Access note:** Direct CEPR fetch was intermittently Cloudflare-blocked; content verified via CEPR page text and a public mirror.  
**Companion theory paper (interpretation, not the first replication target):** Beaudry, Cavallino & Willems (2025), Bank of England Staff Working Paper No. 1117 / BIS Working Paper No. 1246.  
**Closely related event-study (cited, not the target):** Christensen & Rudebusch (2026), SF Fed WP 2026-19 / Hutchins WP 112.  
**Method ancestor:** Hillenbrand, S. (2025), *Review of Financial Studies* 38(4).

Versions used for this guide are the publicly posted PDFs/HTML retrieved on **22 Sep 2026**. No official replication package for the VoxEU column was located.

---

## 1. What the column is — and is not

| Layer | Content | Role in this project |
|---|---|---|
| **Column’s own empirics** | Cumulative yield changes in 3-day windows around NFP + selected Fed Board speeches, Aug 2020–Sep 2026 | **Primary replication target** |
| **Cited findings (CR 2026)** | Fiscal windows ≪ 20% of rise; AI windows negative; post-2021 FOMC windows do not explain the rise | Context / optional side checks; do **not** treat CR’s sample or event lists as the column’s design |
| **Cited findings (Hillenbrand 2025)** | Pre-COVID secular decline concentrated in FOMC 3-day windows | Method template |
| **Theory (Beaudry et al. 2025)** | Interest-income / life-cycle channel → weak r* anchor; self-validating “higher for longer” | Separate optional project |

Do not replicate Christensen–Rudebusch’s fiscal/AI calendars and call that a replication of this column. Do not treat the FLANK model as required for the event-window numbers.

---

## 2. Research question, finding, mechanism

**Question.** After August 2020, long-term US rates rose by hundreds of basis points. Standard theory says, with stable long-run inflation expectations, persistent long-rate moves should mainly reflect r* (demographics, productivity, safe-asset supply/demand). Can fiscal or AI news about r* explain the rise? If not, can *non-r\** news that markets watch for the *near-term policy path* account for the cumulative move?

**Headline empirical finding (descriptive).** Over 1 Aug 2020–3 Sep 2026, combined NFP + Board-speech windows cover **23.9%** of trading days but account for:

- **90.5%** of the rise in the 10-year nominal Treasury yield  
- **91.3%** of the rise in the nominal 5y5y forward  
- **81.0%** of the rise in the average expected short rate over the next 10 years (SF Fed CR decomposition)

**Proposed explanation (theoretical).** Persistent policy-path perceptions can move long real rates because retirement-saving motives create an “interest income effect” that offsets conventional contractionary channels when rates stay high. Misperceptions of r* then correct slowly and can become self-fulfilling. This is offered as *one* explanation consistent with the event-window pattern; the event shares alone do not identify it.

---

## 3. Concepts (intuition first)

**Nominal yield** — quoted Treasury rate. Moves with expected future short rates, expected inflation, and term premiums.

**Real yield** — nominal yield adjusted for inflation compensation (e.g. TIPS or breakevens). The column’s headline charts emphasise *nominal* series plus a model-based expected-short-rate path.

**r\*** (natural / neutral rate) — real short rate consistent with stable inflation and output at potential in the medium run. Slow-moving in textbook stories; unobserved and model-/survey-dependent in practice.

**Expected future short rates** — the path of policy (and short market rates) investors price in. The column stresses that NFP and speeches mainly revise this path.

**Term premium** — extra yield for duration/risk beyond expected short rates. The SF Fed CR series subtracts an estimated term premium so that “average expected overnight rate over 10 years + term premium ≈ observed 10y” (residual folded into the premium on their website).

**5y5y forward** — the implied 5-year rate five years ahead. More “long-run” than the current 10y spot; still not a pure r* measure.

---

## 4. What is measured and how the headline is calculated

### 4.1 Series

1. **10-year nominal Treasury yield** (column Figure 1/2). Exact series ID not stated in the column; Hillenbrand uses GSW off-the-run zeros; CR/H.15 on-the-run constant maturity (FRED `DGS10`) is a common public substitute — document which we use.  
2. **Nominal 5y5y forward** — construction not detailed in the column; Hillenbrand builds from GSW.  
3. **Average expected short rate over 10 years** — explicitly from [SF Fed Treasury Yield Premiums](https://www.frbsf.org/research-and-insights/data-and-indicators/treasury-yield-premiums/) (Christensen–Rudebusch AFNS), per footnote 1. **Do not silently swap in NY Fed ACM.**

### 4.2 Events

1. **NFP / Employment Situation** release dates; **exclude 10 Mar 2023** (SVB).  
2. **Speeches** by “prominent monetary policymakers at the Federal Reserve Board,” specifically (footnote 4):  
   - Chair: Jerome Powell until May 2026; Kevin Warsh thereafter  
   - Vice Chair: Clarida until Jan 2022; Brainard May 2022–Feb 2023; Jefferson from Sep 2023  
   - Governor Christopher Waller  
   Ambiguities (speech vs testimony; after-hours dating; regional Fed presidents excluded) → assumptions log.

### 4.3 Window convention (critical)

Figure note: event windows “only consider changes from the close of day at **(T−1)** to the close of day at **(T+1)**,” where T is the event day.

That wording is a **two-session** return:  
\(\Delta^{close}_{T-1 \to T+1} y = y_{T+1} - y_{T-1}\)  
which equals the sum of *daily* changes on days **T** and **T+1** only.

Hillenbrand (2025) and CR (2026) instead treat **days {T−1, T, T+1}** as event days and accumulate *three* daily changes (with unique-day de-duplication when windows overlap).

**Assumption A1 (open):** implement both conventions; label them `close_span_Tm1_Tp1` vs `days_Tm1_T_Tp1`. Do not pick the one that matches 90.5% without documenting it.

### 4.4 Cumulative paths and shares

Let \(y_t\) be the series on trading day \(t\), sample \(t = 0,\ldots,N\) with \(t=0\) = 1 Aug 2020 (or first available trading day on/after), end = 3 Sep 2026.

Daily change: \(\Delta y_t = y_t - y_{t-1}\).

Let \(E\) be the set of trading days that fall inside at least one event window (union — **no double-counting**).

**Event-only path** (Hillenbrand-style):

\[
\tilde y_t = y_0 + \sum_{s=1}^{t} \mathbf{1}\{s \in E\}\,\Delta y_s
\]

**Non-event path:** same with \(\mathbf{1}\{s \notin E\}\).

**Share of total movement:**

\[
S = \frac{\sum_{s=1}^{N} \mathbf{1}\{s \in E\}\,\Delta y_s}{\sum_{s=1}^{N} \Delta y_s} = \frac{\tilde y_N - y_0}{y_N - y_0}
\]

**Share of trading days:** \(|E|/N\).

**Identity check:** event cumulative change + non-event cumulative change = total change.

### 4.5 Illustrative numerical example (fake data — not study numbers)

Suppose three trading days after \(y_0=1.00\%\):

| Day | Event? | \(y_t\) | \(\Delta y\) |
|---|---|---|---|
| 1 | yes | 1.10 | +0.10 |
| 2 | no | 1.05 | −0.05 |
| 3 | yes | 1.25 | +0.20 |

Total rise = \(0.25\). Event-day sum = \(0.30\). Share \(S = 0.30/0.25 = 120\%\).  
Non-event sum = \(−0.05\). Note \(S\) can exceed 100% when outside-window moves reverse inside-window moves. **A large share is not a causal fraction of a decomposition of independent shocks.**

---

## 5. What the empirics establish vs assumption-laden claims

| Statement | Status |
|---|---|
| Yield changes are concentrated on the authors’ event-day set | **Descriptive**; replicable in principle |
| Concentration ≫ day share (23.9% vs ~80–90%) | Descriptive; still needs calendar fidelity |
| Events “caused” that share of the rise | **Not established** by the share statistic |
| News is about the policy path, not r* | **Partially supported** if expected-short-rate series moves similarly; still not a full causal ID |
| r* is weakly anchored / self-fulfilling | **Theoretical interpretation** (BoE/BIS paper) |
| Useful as a real-time trading rule | **Not established**; and would require real-time calendars + no look-ahead |

---

## 6. Conditional implications (three cases)

### Case A — Descriptive finding *and* mechanism both hold

Long rates can drift with policy-communication narratives even when “secular” r* drivers are quiet. Macro work should separate *policy-path news days* from *r\*-candidate news*. Scenario analysis for duration risk should stress speech/NFP clusters, not only FOMC. Still: no automatic forecast of the *sign* of the next event.

### Case B — Descriptive concentration holds; mechanism uncertain

Still useful: a monitoring map of which days historically carried the trend. Competing stories (selection of high-volatility days; endogenous speech timing; omitted macro releases inside windows; term-structure model artefacts) remain live. Do **not** conclude that r* “doesn’t matter” or that speeches “set” r*.

### Case C — Finding sensitive to data/method choices

If shares collapse under alternative windows, speech filters, or yield definitions, treat the published 80–90% as **fragile**. Retain the methodological lesson (always check event-day concentration) without importing the column’s magnitudes into policy or risk narratives.

---

## 7. Use cases (with limits)

1. **Macro research** — Question: did the post-2020 yield rise arrive as a slow r* revision or as lumpy news days? Output: event vs non-event cumulative paths. Need: robustness to calendars; comparison to CPI, FOMC, fiscal dates.  
2. **Monetary transmission** — Question: which communication channels moved the long end after 2020? Output: NFP vs speech vs FOMC shares. Need: surprise measures (payroll surprise, speech “hawkishness”) for causal step-up.  
3. **Fixed-income risk / scenarios** — Question: historically, how much of a multi-year selloff clustered on known event types? Output: contribution tables. Need: explicit statement this is retrospective attribution, not VaR calibration without further work.  
4. **Monitoring** — Question: when do markets reprice the path? Output: live calendar + realised window moves. Need: real-time speech classification rules fixed *ex ante*.

---

## 8. Evidence evaluation checklist

- **Reproducible?** Pending data + calendar (see inventory).  
- **Robust?** Planned: ±1 day windows; NFP-only / speeches-only; reinstate 10 Mar 2023; drop Waller or add other governors; FOMC placebo; randomised event dates preserving monthly frequency (Hillenbrand-style).  
- **Causal?** Weak with current design; speeches may be scheduled when markets are unsettled; windows contain other news.  
- **Predictive / investable?** Not shown; do not infer alpha from historical concentration.

**Placebo null (planned):** randomly place the same *number* of events with similar spacing/overlap constraints; distribution of \(S\) under the null that event labels are unrelated to the trend. A naive “random dates ignore clustering” test is insufficient.

---

## 9. Replication order

1. Lock sample dates and trading calendar.  
2. Ingest yields + SF Fed expected-short-rate series; build 5y5y.  
3. Build NFP calendar (− SVB date).  
4. Build Board speech calendar (speaker filter).  
5. Implement both window conventions; union of event days.  
6. Recompute shares + Figure 2–style chart → [`results_comparison.md`](results_comparison.md).  
7. Robustness + placebo.  
8. Optional: FLANK/theory replication (out of scope for v1).

---

## 10. How to rerun (once code lands)

See project `README.md`. Stages: acquire → clean → calendars → baseline → figures → robustness. Config drives dates, series IDs, and window mode. Raw inputs stay in `data/raw/`; derived outputs in `data/derived/` and `output/`.

**Status as of 22 Sep 2026:** documentation and source audit only; analysis code **not yet executed** (awaiting confirmation before implementation).
