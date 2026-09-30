# Assumptions log

Unresolved or under-documented choices. Prefer testing alternatives over silently matching published numbers.

| ID | Topic | What the sources say | Our working rule | Status | Sensitivity plan |
|---|---|---|---|---|---|
| A1 | “Three-day window” math | Figure note: close(T−1)→close(T+1). Hillenbrand/CR: accumulate daily changes on {T−1,T,T+1}. | Implement **both**; report both shares | Open | Primary discrepancy to publish if only one matches ~90% |
| A2 | Overlapping windows | CR notes unique event-window days after overlap | Use set-union of trading days in any window; never sum the same \(\Delta y_t\) twice | Locked | Count \|E\| vs naive 3×#events |
| A3 | Weekend / holiday events | CR: centre on nearest business day; window = three business sessions | Same if a speech falls on non-trading day | Locked pending speech times | Log remapped dates |
| A4 | After-hours speeches | Undocumented in column | Default: event date = calendar date of speech start in ET; if after 16:00 ET US, set T = next trading day | Open | Alt: always speech calendar date |
| A5 | Speech universe | Footnote 4 names offices/people; not “all public remarks” vs prepared speeches vs testimony | Include prepared speeches + congressional testimony listed on Fed site for named officials; exclude interviews/media Q&A unless on speeches page | Open | Narrow to “Speeches” only; widen to all Board governors |
| A6 | Vice Chair gaps | Clarida ends Jan 2022; Brainard May 2022–Feb 2023; Jefferson from Sep 2023 — gaps exist | No substitute speakers during gaps | Locked to footnote | Fill gaps with Acting VC if any |
| A7 | Chair transition | Powell until May 2026; Warsh since | Switch on Warsh confirmation/start date (verify exact day) | Open — exact day not in column | ±1 week around May 2026 |
| A8 | NFP exclusion | Drop 10 Mar 2023 only | Baseline drops it; robustness restores it | Locked | Report both |
| A9 | 10y series | Column unspecified | Prefer GSW 10y zero if obtainable; else FRED `DGS10` as **approximate** | Open / blocked fetch | Parallel series if both available |
| A10 | 5y5y construction | Column unspecified; Hillenbrand uses GSW | Match Hillenbrand GSW instantaneous forward when possible | Open | FRED forward substitutes labelled approx |
| A11 | Expected short rate | Footnote 1 → SF Fed CR premiums, not ACM | SF Fed only for “exact”; ACM = approximate fallback | Locked intent | Side-by-side if both exist |
| A12 | Sample start alignment | “1 August 2020” — weekend | First trading day on/after 2020-08-01 | Locked | Check cumulative from 2020-07-31 close |
| A13 | Sample end | Last data 3 Sep 2026 | End on that trading day | Locked for baseline | Extension = separate run |
| A14 | Share denominator | Total change \(y_N-y_0\); can be small or partially offset | Always report event bp, non-event bp, and \(S\); flag if \|outside\| large | Locked | |
| A15 | Placebo design | Hillenbrand: monthly count-matched random days | Match #events per month and rebuild windows with overlap | Planned | Avoid iid random dates only |

## Decision rule

Do **not** choose an open assumption solely because it reproduces 90.5 / 91.3 / 81.0. If a choice is required to proceed, pick the rule closest to Hillenbrand/CR prose, label it, and show the alternative.
