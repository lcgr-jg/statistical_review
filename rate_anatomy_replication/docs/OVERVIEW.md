# Anatomy of a rise — one-page overview

**Source:** Beaudry, Cavallino & Willems, VoxEU/CEPR, 21 Sep 2026. Mirror used when CEPR blocked. **Not found:** author replication package.

### What is this study saying?

The authors ask why US long-term yields rose sharply after mid-2020 if “fundamentals” that set r* usually move slowly. **Observed:** from 1 Aug 2020 to 3 Sep 2026, three-day windows around nonfarm payroll (NFP) releases and selected Federal Reserve Board speeches cover about **24% of trading days** but account for roughly **90%** of the rise in the 10-year yield and 5y5y forward, and **81%** of the rise in model-based average expected short rates (they drop the 10 Mar 2023 payroll / SVB week). **Proposed cause:** these events revise the *policy path*, not r*; companion theory argues r* anchors long rates only weakly, so policy beliefs can self-validate. That mechanism is interpretation, not identified by the event-share numbers.

### How did they investigate it?

They adapt Hillenbrand (2025): keep yield changes only inside event windows, zero the rest, and compare that cumulative rise to the full-sample rise. Series: 10-year Treasury, nominal 5y5y forward, and the SF Fed CR-model average expected short rate over 10 years. Speeches: Chair (Powell then Warsh), Vice Chair (Clarida / Brainard / Jefferson), and Governor Waller. Replication means rebuilding those calendars and recomputing shares without double-counting overlaps.

### Why should I care?

1. **Macro reading:** push back on treating every long-rate move as “r* up.”  
2. **Transmission:** after 2020, payrolls and Board speeches—not only FOMC days—look like long-end coordination points (cited work finds FOMC windows do *not* explain the post-Covid rise).  
3. **Scenarios:** helps attribute historical selloffs; **not** a forecast or trading rule.

If only the descriptive concentration holds, the calendar still matters for monitoring; weak-r* claims remain optional.

### What do we need to replicate it?

Essential inputs: daily 10y / curve for 5y5y (FRED or GSW); SF Fed Treasury Yield Premiums expected-short-rate series; BLS NFP dates; Fed Board speech dates for the named officials. All are public in principle. **Verified:** source pages located. **Not yet retrieved here:** FRED CSV (timeout) and Fed GSW (403). Speech eligibility remains partly ambiguous. Full inventory: [`data_inventory.md`](data_inventory.md).

### How much confidence should we have?

**Strengths:** clear headline design; window formula in the figure note; sits on a published method. **Limits:** speech rules under-documented; “share of total move” ≠ causation and can exceed 100% when outside-window moves reverse; expected-short-rate path is model-based. Matching published percentages would reproduce a chart, not validate the theoretical mechanism.

### What is our next step?

**Smallest useful target:** Figure 2–style cumulative paths and the three published shares for the original sample. **Main blocker:** verified premiums file + a defensible speech calendar. **Feasibility:** approximate public-data replication looks workable; exact match is uncertain until window conventions and speech filters are locked. **Progress:** sources audited; docs scaffolded; analysis code not yet written (confirmation requested).

**Deeper:** [research guide](RESEARCH_GUIDE.md) · [replication spec](replication_spec.md) · [data inventory](data_inventory.md) · [assumptions log](assumptions_log.md) · [results](results_comparison.md) · [blockers](robustness_and_blockers.md)
