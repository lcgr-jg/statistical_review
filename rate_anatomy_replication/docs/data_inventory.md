# Data inventory

Retrieval checks run **22 Sep 2026**. Status codes: **located** (URL known) · **documented** (fields/method described) · **retrieved** (file on disk and inspected) · **blocked** (attempt failed).

| ID | Role | Definition / series | Provider & link | ID / file | Freq / units | Coverage needed | Transform | Access | Cost / creds | Access tested? | Vintage / revision | Limits for replication | Local path |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Y10 | Headline 10y nominal | Constant-maturity or GSW 10y zero | FRED / Fed Board | `DGS10` or GSW `SVENY10` | Daily, % | 2020-08-01 → 2026-09-03 | Level; daily Δ | Public | Free | **Blocked:** FRED timeout; GSW HTTP 403 from this host | FRED is revised H.15; GSW re-estimated historically | Series choice may shift bps vs authors | `data/raw/fred_dgs10.csv` (pending) |
| F5Y5Y | Nominal 5y5y forward | Implied 5y rate 5y ahead | Construct from GSW (Hillenbrand) or published forwards | GSW params / `THREEFY5Y` variants | Daily, % | Same | Instantaneous/par forward formula TBD | Public | Free | Not retrieved | Depends on curve method | Column silent on exact construction → **approx** unless GSW used | `data/derived/fwd_5y5y.parquet` |
| ESR10 | Avg expected short rate, 10y | CR AFNS “Average Expected Overnight Rate” 10y | [SF Fed Treasury Yield Premiums](https://www.frbsf.org/research-and-insights/data-and-indicators/treasury-yield-premiums/) | Excel “Website Chart Data” / “Complete Model Data” | Daily, % | Same | Level; daily Δ | Public Excel | Free | **Located + documented; download not yet retrieved** | Model re-estimated daily since 1998 (real-time style per site) | **Do not substitute NY Fed ACM** without labelling approximate | `data/raw/sf_fed_*.xlsx` (pending) |
| TP10 | Context / decomposition | 10y term premium (CR) | Same SF Fed page | Companion column in Excel | Daily, % | Same | Optional | Public | Free | Same as ESR10 | Model-based | Residual folded into premium on website | same workbook |
| NFP | Event dates | Employment Situation release calendar | BLS | Release calendar / ALFRED | Monthly dates | Sample | Drop 2023-03-10 | Public | Free | Located; calendar not yet built | Release time 8:30 ET — window is close-to-close | Must confirm holiday shifts | `data/raw/nfp_dates.csv` |
| SPCH | Event dates | Speeches by Chair, Vice Chair, Waller | federalreserve.gov speeches | HTML archive by speaker | Irregular | Sample | Map to trading day T; union windows | Public | Free | Located; scrape not run | After-hours → which close? | Eligibility rules incomplete (see assumptions) | `data/raw/fed_board_speeches.csv` |
| FOMC | Robustness / CR contrast | Scheduled FOMC announcement days | Fed FOMC calendars | Meeting end dates | ~8/year | Optional | 3-day windows | Public | Free | Page retrieved 22 Sep 2026 | Pre/post-1994 dating N/A here | Not in baseline event set | `data/raw/fomc_dates.csv` |
| TRCAL | Trading calendar | US government bond trading days | Inferred from yield series non-missing dates | — | Daily | Sample | Drop weekends/holidays with no quote | Derived | Free | Depends on Y10 retrieval | Half-days rare for these series | Overlaps handled via unique dates in \(E\) | `data/derived/trading_calendar.parquet` |

## Exact vs approximate vs extension

1. **Exact (target):** SF Fed CR expected-short-rate series + authors’ speech list + same 10y/5y5y definition + sample end 3 Sep 2026.  
2. **Approximate (documented substitutes):** FRED `DGS10` instead of GSW 10y; NY Fed ACM `ACMY10` only if SF Fed file stays unavailable — label clearly.  
3. **Extensions:** sample update past 3 Sep 2026; CPI/FOMC/fiscal calendars; surprise regressions; theory model.

## Observed vs model estimates

| Object | Type |
|---|---|
| Treasury yields / forwards from curve | Observed (curve-fit) |
| SF Fed average expected short rate | **Model estimate** (AFNS) |
| r* narratives in the theory section | Unobserved; not required for baseline shares |

## Real-time vs revised

SF Fed states CR premiums are re-estimated daily with information up to that date — closer to real-time than a single full-sample smoother. FRED `DGS10` is standard published H.15. Speech calendars are knowable in real time; classifying “eligible speech” *ex ante* is the hard part for any monitoring use case.

## Provenance log

| Timestamp (UTC) | Action | Result |
|---|---|---|
| 2026-09-22 | CEPR column fetch | Cloudflare block; succeeded later / via mirror |
| 2026-09-22 | FRED `DGS10` CSV | Timeout (PowerShell + urllib) |
| 2026-09-22 | Fed GSW `feds200628.csv` | HTTP 403 |
| 2026-09-22 | SF Fed premiums page | HTML OK; Excel href scrape pending successful download |
| 2026-09-22 | Fed FOMC calendar page | Retrieved |
