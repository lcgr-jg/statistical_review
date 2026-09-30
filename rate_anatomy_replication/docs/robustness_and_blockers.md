# Robustness and blocker record

## Blockers (current)

| Blocker | Impact | Workaround |
|---|---|---|
| FRED `DGS10` download timeout from this environment | No yield series on disk | Manual download, Bloomberg desk pull, or retry later |
| Fed GSW CSV HTTP 403 | Preferred curve / 5y5y blocked | Same; or use any already-licensed market-data cache with clear labelling |
| SF Fed premiums Excel not yet retrieved | Cannot hit 81.0% ESR target exactly | Page confirmed; manual download; ACM only as **approximate** fallback |
| No author speech list / replication package | Speech calendar ambiguous | Build from Fed site + footnote 4; log inclusions |
| Window math ambiguity (A1) | Two plausible “3-day” definitions | Implement both |

## Robustness tests (planned / status)

| Test | Null / question | Status |
|---|---|---|
| W1 vs W2 windows | Does “3-day” wording change shares? | Planned |
| NFP-only vs speeches-only | Which category drives the share? | Planned |
| Reinstate 10 Mar 2023 NFP | Did SVB exclusion matter? | Planned |
| Drop Waller / add other governors | Speaker filter sensitivity | Planned |
| ± expand to 5- or 7-day windows | Microstructure vs trend | Planned |
| FOMC windows only (CR-style) | Confirm FOMC does not explain rise in *this* sample | Planned |
| Placebo: month-matched random events | Is concentration distinguishable from chance given event frequency & overlap? | Planned |
| Alternate yield (DGS10 vs GSW) | Series dependence | Planned |
| ACM vs SF Fed ESR | Model dependence | Planned only if SF Fed missing |

## What changed when tested

*No empirical tests run yet.*

## Still uncertain

- Exact Warsh start date used by authors  
- Whether testimony counts as a “speech”  
- After-hours dating rule  
- Exact 5y5y formula in the column’s Figure 2  

## Additional evidence that would help mechanism claims

- Intraday or narrow surprise regressions (payroll surprise → yield)  
- Speech tone / hawkishness measures  
- Explicit controls for other releases inside the same windows  
- Survey-based policy-rule perceptions around the same dates (Bauer–Pflueger–Sunderam style)
