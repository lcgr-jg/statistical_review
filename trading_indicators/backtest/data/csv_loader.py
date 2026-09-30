"""
CSV Data Loader
===============
Load OHLCV data from CSV files exported from Bloomberg, IB, or TradingView.
Handles various column naming conventions and date formats.
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Column name mappings for common export formats
COLUMN_MAPS = {
    # Bloomberg BDH export
    "PX_OPEN": "open", "PX_HIGH": "high", "PX_LOW": "low",
    "PX_LAST": "close", "VOLUME": "volume",
    # TradingView export
    "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
    # IB export
    "OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close", "VOL": "volume",
    # Generic
    "Date": "date", "Time": "time", "DateTime": "datetime",
    "Datetime": "datetime", "DATE": "date", "TIME": "time",
    "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
}


def load_csv(filepath: str, date_col: str = None,
             datetime_format: str = None) -> pd.DataFrame:
    """
    Load OHLCV data from any common CSV format.

    Args:
        filepath: Path to CSV file
        date_col: Override date column name detection
        datetime_format: Override datetime parsing format

    Returns:
        Standardized DataFrame with: datetime, date, open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df)} rows from {filepath}")
    print(f"Columns found: {list(df.columns)}")

    # Normalize column names
    rename_map = {}
    for col in df.columns:
        stripped = col.strip()
        if stripped in COLUMN_MAPS:
            rename_map[col] = COLUMN_MAPS[stripped]
        elif stripped.lower() in ["open", "high", "low", "close", "volume", "date", "time", "datetime"]:
            rename_map[col] = stripped.lower()
    df = df.rename(columns=rename_map)

    # Find and parse datetime
    if date_col:
        df["datetime"] = pd.to_datetime(df[date_col], format=datetime_format)
    elif "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    elif "date" in df.columns and "time" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    elif "date" in df.columns:
        df["datetime"] = pd.to_datetime(df["date"])
    else:
        # Try first column as datetime
        try:
            df["datetime"] = pd.to_datetime(df.iloc[:, 0])
        except Exception:
            raise ValueError("Cannot detect date/time column. Specify date_col parameter.")

    df["date"] = df["datetime"].dt.date

    # Validate required columns
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if "volume" not in df.columns:
        print("Warning: No volume column found, setting to 0")
        df["volume"] = 0

    # Clean numeric data
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df.sort_values("datetime").reset_index(drop=True)

    print(f"Cleaned: {len(df)} bars from {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    return df


def generate_sample_data(bars: int = 1000, start_price: float = 5000,
                         volatility: float = 0.001,
                         trend: float = 0.0001) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for testing when you don't have real data yet.
    Simulates realistic futures price action with trends, mean reversion, and volume patterns.
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-02 09:30", periods=bars, freq="h")

    # Price simulation with regime changes
    close_prices = [start_price]
    regime = 1  # 1=trending up, -1=trending down, 0=range
    regime_duration = 0

    for i in range(1, bars):
        # Random regime changes
        regime_duration += 1
        if regime_duration > np.random.randint(50, 150):
            regime = np.random.choice([-1, 0, 1])
            regime_duration = 0

        drift = trend * regime
        shock = np.random.normal(0, volatility)
        # Add mean reversion component
        mean_rev = -0.001 * (close_prices[-1] - start_price) / start_price
        change = drift + shock + mean_rev * 0.1
        close_prices.append(close_prices[-1] * (1 + change))

    close_arr = np.array(close_prices)
    # Generate OHLV from close
    high_arr = close_arr * (1 + np.abs(np.random.normal(0, volatility * 0.5, bars)))
    low_arr = close_arr * (1 - np.abs(np.random.normal(0, volatility * 0.5, bars)))
    open_arr = np.roll(close_arr, 1)
    open_arr[0] = start_price

    # Volume: higher on big moves, higher at open/close
    base_vol = 10000
    move_vol = np.abs(np.diff(close_arr, prepend=close_arr[0])) / close_arr * 100000
    time_vol = np.array([1.5 if h in [9, 10, 15] else 1.0 for h in dates.hour])
    volume = (base_vol + move_vol) * time_vol * np.random.uniform(0.8, 1.2, bars)

    df = pd.DataFrame({
        "datetime": dates,
        "date": dates.date,
        "open": np.round(open_arr, 2),
        "high": np.round(high_arr, 2),
        "low": np.round(low_arr, 2),
        "close": np.round(close_arr, 2),
        "volume": volume.astype(int),
    })

    # Ensure OHLC consistency
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate sample data")
    parser.add_argument("--file", default=None, help="CSV file to load")
    parser.add_argument("--bars", type=int, default=1000, help="Bars for sample data")
    args = parser.parse_args()

    if args.generate:
        df = generate_sample_data(bars=args.bars)
        out = "data/sample_ES_1h.csv"
        df.to_csv(out, index=False)
        print(f"Generated {len(df)} sample bars -> {out}")
    elif args.file:
        df = load_csv(args.file)
        print(df.head(10))
        print(f"\nStats:\n{df[['open','high','low','close','volume']].describe()}")
