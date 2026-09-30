# rate_anatomy_replication

Research collaboration: understand, critique, and (where feasible) replicate  
**Beaudry, Cavallino & Willems (VoxEU, 21 Sep 2026)** — “Anatomy of a rise…”

## Start here

1. **[docs/OVERVIEW.md](docs/OVERVIEW.md)** — ≤500-word entry point  
2. [docs/RESEARCH_GUIDE.md](docs/RESEARCH_GUIDE.md) — concepts, method, implications  
3. [docs/replication_spec.md](docs/replication_spec.md) — exact replication target  
4. [docs/data_inventory.md](docs/data_inventory.md) — sources & access status  
5. [docs/assumptions_log.md](docs/assumptions_log.md) — open methodological choices  

## Layout

```
rate_anatomy_replication/
  docs/           # overview + guides
  data/raw/       # immutable downloads
  data/derived/   # cleaned series, calendars
  notebooks/      # explanatory analysis (planned)
  src/            # reusable logic (planned)
  scripts/        # one-off probes
  output/         # figures & comparison tables
```

## Status (22 Sep 2026)

- Sources read and documented.  
- Public data URLs located; automated downloads from this environment **not yet successful** (FRED timeout, Fed GSW 403).  
- Analysis code **not implemented** — awaiting confirmation (see chat).

## Primary sources

- [VoxEU column](https://cepr.org/voxeu/columns/anatomy-rise-monetary-policy-and-post-covid-surge-long-term-interest-rates)  
- [SF Fed Treasury Yield Premiums](https://www.frbsf.org/research-and-insights/data-and-indicators/treasury-yield-premiums/)  
- Hillenbrand (2025), RFS; Christensen & Rudebusch (2026), SF Fed WP 2026-19; Beaudry et al. (2025), BoE WP 1117
