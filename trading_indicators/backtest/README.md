# Trading Strategy Backtester

A Python backtesting framework for comparing **Breakout**, **Momentum**, and **Mean Reversion** strategies across CME futures — with Bloomberg and Interactive Brokers data pipelines.

## Project Structure

```
backtest/
├── config.py                 # All parameters in one place
├── run_backtest.py           # Main entry point
├── run_comparison.py         # Compare all 3 strategies side-by-side
├── data/
│   ├── bloomberg_pipeline.py # Pull data via Bloomberg API (BDH/BDP)
│   ├── ib_pipeline.py        # Pull data via IB TWS/Gateway API
│   └── csv_loader.py         # Load from exported CSV files
├── strategies/
│   ├── base.py               # Base strategy class
│   ├── breakout.py           # Breakout strategy
│   ├── momentum.py           # Momentum strategy
│   └── mean_reversion.py     # Mean reversion strategy
├── utils/
│   ├── indicators.py         # ATR, RSI, VWAP, Bollinger, etc.
│   ├── risk.py               # Position sizing & risk management
│   └── metrics.py            # Performance analytics
└── README.md
```

## Quick Start

### Option 1: Using CSV data (simplest)
Export OHLCV data from Bloomberg or IB to CSV with columns:
`date, open, high, low, close, volume`

```python
python run_backtest.py --source csv --file data/ES_1h.csv --strategy breakout
```

### Option 2: Bloomberg Terminal (requires blpapi)
```python
python run_backtest.py --source bloomberg --ticker "ESA Index" --strategy momentum
```

### Option 3: Interactive Brokers (requires ib_insync)
```python
python run_backtest.py --source ib --symbol ES --strategy mean_reversion
```

### Compare All Strategies
```python
python run_comparison.py --source csv --file data/ES_1h.csv
```

## Setup

```bash
pip install pandas numpy matplotlib

# For Bloomberg:
# Install blpapi from Bloomberg (requires terminal license)
# pip install blpapi

# For Interactive Brokers:
# pip install ib_insync
```

## Configuration

Edit `config.py` to set:
- Account size, risk per trade, max daily loss
- Strategy-specific parameters (lookback periods, thresholds)
- Bloomberg/IB connection settings
- Data timeframes and date ranges
