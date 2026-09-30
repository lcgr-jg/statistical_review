# Replication specification — event-window baseline

## Target paper

Beaudry, Cavallino, Willems (VoxEU, 21 Sep 2026). Empirics only. Theory model = optional later project.

## Sample (fixed for baseline)

| Item | Value |
|---|---|
| Start | 1 Aug 2020 (first trading day on/after) |
| End | 3 Sep 2026 |
| Market | US Treasuries |
| Extension past end date | Separate run only |

## Series and transforms

| Output name | Preferred input | Transform |
|---|---|---|
| `y10` | GSW 10y zero or FRED `DGS10` | Daily level; \(\Delta_t = y_t - y_{t-1}\) |
| `fwd_5y5y` | GSW-based nominal 5y5y | Same |
| `esr10` | SF Fed CR avg expected overnight rate, 10y | Same |

Units: percentage points; report cumulative moves in **basis points** (×100) for comparison tables.

## Event categories

### NFP

- All Employment Situation release dates in sample.  
- **Exclude:** 10 Mar 2023.  
- Centre T = release date (trading day).

### Fed Board speeches

Include remarks by:

1. Chair Jerome Powell (until May 2026)  
2. Chair Kevin Warsh (from May 2026)  
3. Vice Chair Richard Clarida (until Jan 2022)  
4. Vice Chair Lael Brainard (May 2022–Feb 2023)  
5. Vice Chair Philip Jefferson (from Sep 2023)  
6. Governor Christopher Waller (full sample in office)

Selection/exclusion details beyond footnote 4: see assumptions **A5–A7**.

### Not in baseline event set

FOMC decisions, CPI, fiscal, AI dates (optional robustness / CR comparison).

## Window definitions (implement both)

**W1 — Figure-note span:** event contribution on day \(t\) if \(t \in \{T, T+1\}\) for some event date T (equiv. accumulate \(y_{T+1}-y_{T-1}\) once per event, but **de-duplicate days** across events via union).  

**W2 — Hillenbrand/CR days:** event days \(t \in \{T-1, T, T+1\}\).

Holiday/weekend centring: assumptions **A3–A4**.

## Headline published results to match

| Statistic | Published |
|---|---|
| Trading-day coverage | 23.9% |
| Share of 10y rise | 90.5% |
| Share of 5y5y rise | 91.3% |
| Share of ESR10 rise | 81.0% |
| Figure 2 | Cumulative actual vs event-only paths |

Secondary narrative claims (fiscal <20%, AI negative, FOMC ≈0) are **CR’s** results — optional cross-check, not success criteria for this replication.

## Reproduction order

1. Trading calendar from yield series  
2. Ingest `y10`, `fwd_5y5y`, `esr10`  
3. NFP calendar − SVB date  
4. Speech calendar  
5. Build \(E\) under W1 and W2  
6. Cumulative paths, shares, day coverage  
7. Reconcile event + non-event = total  
8. Compare to table above → `results_comparison.md`  
9. Robustness (windows, categories, SVB in, placebo)

## Formulas

See [RESEARCH_GUIDE.md §4.4](RESEARCH_GUIDE.md). Overlaps: \(E = \bigcup_i W(T_i)\).

## Success criteria

| Level | Criterion |
|---|---|
| Smoke | Code runs; identity check holds |
| Approximate | Same qualitative story (event share ≫ day share); same sign |
| Exact | Shares within a few percentage points of 90.5 / 91.3 / 81.0 and ~23.9% day share under a documented calendar |

Exact success is **not** required to finish v1 documentation or an approximate pipeline.
