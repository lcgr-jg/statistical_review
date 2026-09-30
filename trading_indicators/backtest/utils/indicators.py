"""
Technical indicators used across all strategies.
All functions take a pandas DataFrame with columns: open, high, low, close, volume
and return the DataFrame with new indicator columns added.
"""
import pandas as pd
import numpy as np


def atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average True Range — measures volatility."""
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([
        h - l,
        (h - c.shift(1)).abs(),
        (l - c.shift(1)).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(period).mean()
    df["tr"] = tr
    return df


def rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Relative Strength Index."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def ema(df: pd.DataFrame, period: int, col: str = "close", name: str = None) -> pd.DataFrame:
    """Exponential Moving Average."""
    name = name or f"ema_{period}"
    df[name] = df[col].ewm(span=period, adjust=False).mean()
    return df


def sma(df: pd.DataFrame, period: int, col: str = "close", name: str = None) -> pd.DataFrame:
    """Simple Moving Average."""
    name = name or f"sma_{period}"
    df[name] = df[col].rolling(period).mean()
    return df


def bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands — measures volatility envelope."""
    df["bb_mid"] = df["close"].rolling(period).mean()
    rolling_std = df["close"].rolling(period).std()
    df["bb_upper"] = df["bb_mid"] + (rolling_std * std_dev)
    df["bb_lower"] = df["bb_mid"] - (rolling_std * std_dev)
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    df["bb_pct"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])
    return df


def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD — Moving Average Convergence Divergence."""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd_line"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd_line"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_signal"]
    return df


def vwap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volume Weighted Average Price.
    Resets daily if intraday data has a 'date' column or detectable day boundaries.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    if "date" in df.columns:
        groups = df.groupby("date")
        vwap_vals = []
        for _, group in groups:
            cum_vol = group["volume"].cumsum()
            cum_tp_vol = (typical_price.loc[group.index] * group["volume"]).cumsum()
            vwap_vals.append(cum_tp_vol / cum_vol.replace(0, np.nan))
        df["vwap"] = pd.concat(vwap_vals)
    else:
        cum_vol = df["volume"].cumsum()
        cum_tp_vol = (typical_price * df["volume"]).cumsum()
        df["vwap"] = cum_tp_vol / cum_vol.replace(0, np.nan)
    return df


def donchian_channel(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Donchian Channel — highest high / lowest low over N bars."""
    df["dc_upper"] = df["high"].rolling(period).max()
    df["dc_lower"] = df["low"].rolling(period).min()
    df["dc_mid"] = (df["dc_upper"] + df["dc_lower"]) / 2
    return df


def rate_of_change(df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
    """Rate of Change — percentage change over N periods."""
    df["roc"] = df["close"].pct_change(period) * 100
    return df


def volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Current volume relative to N-period average."""
    df["vol_avg"] = df["volume"].rolling(period).mean()
    df["vol_ratio"] = df["volume"] / df["vol_avg"].replace(0, np.nan)
    return df


def rsi_divergence(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
    """
    Detect bullish/bearish RSI divergence.
    Bullish: price makes lower low, RSI makes higher low
    Bearish: price makes higher high, RSI makes lower high
    """
    if "rsi" not in df.columns:
        df = rsi(df)

    bull_div = pd.Series(False, index=df.index)
    bear_div = pd.Series(False, index=df.index)

    for i in range(lookback, len(df)):
        window_close = df["close"].iloc[i-lookback:i+1]
        window_rsi = df["rsi"].iloc[i-lookback:i+1]

        if (window_close.iloc[-1] < window_close.min() * 1.001 and
                window_rsi.iloc[-1] > window_rsi.iloc[window_close.argmin()]):
            bull_div.iloc[i] = True

        if (window_close.iloc[-1] > window_close.max() * 0.999 and
                window_rsi.iloc[-1] < window_rsi.iloc[window_close.argmax()]):
            bear_div.iloc[i] = True

    df["rsi_bull_divergence"] = bull_div
    df["rsi_bear_divergence"] = bear_div
    return df


def compute_all(df: pd.DataFrame, config=None) -> pd.DataFrame:
    """Compute all indicators needed for all three strategies."""
    from config import BREAKOUT, MOMENTUM, MEAN_REVERSION
    cfg_b = config or BREAKOUT
    cfg_m = config or MOMENTUM
    cfg_r = config or MEAN_REVERSION

    df = atr(df, period=14)
    df = rsi(df, period=14)
    df = ema(df, period=9, name="ema_9")
    df = ema(df, period=21, name="ema_21")
    df = sma(df, period=50, name="sma_50")
    df = sma(df, period=200, name="sma_200")
    df = bollinger_bands(df)
    df = macd(df)
    df = vwap(df)
    df = donchian_channel(df)
    df = rate_of_change(df)
    df = volume_ratio(df)
    df = rsi_divergence(df)
    return df
