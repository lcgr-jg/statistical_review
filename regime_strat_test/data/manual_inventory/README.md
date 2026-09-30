# Manual EIA inventory CSV

If Bloomberg does not return EIA indexes (`DOEUSCR Index`, etc.), export weekly stocks
from the terminal (`EIA <GO>`) or EIA.gov and save as:

`eia_stocks.csv`

```text
date,CL,XB,HO
2015-01-02,400.1,230.5,140.2
2015-01-09,402.3,228.1,141.0
```

Units can be mbbl; only relative seasonality matters for z-scores.
