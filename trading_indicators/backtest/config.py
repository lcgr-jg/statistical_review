"""
Central configuration for backtesting framework.
Edit these values to match your account and preferences.
Blue = inputs you should change. Black = calculated or defaults.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class AccountConfig:
    balance: float = 10_000.0
    risk_per_trade_pct: float = 0.01       # 1% max risk per trade
    max_daily_loss_pct: float = 0.03       # 3% daily stop
    max_open_positions: int = 3
    commission_per_side: float = 1.25      # CME micro futures typical
    slippage_ticks: int = 1                # assume 1 tick slippage per side

    @property
    def risk_per_trade(self) -> float:
        return self.balance * self.risk_per_trade_pct

    @property
    def max_daily_loss(self) -> float:
        return self.balance * self.max_daily_loss_pct


@dataclass
class BreakoutConfig:
    lookback_period: int = 20              # bars for high/low channel
    volume_multiplier: float = 1.3         # volume must be > 1.3x avg
    atr_period: int = 14
    stop_atr_multiple: float = 1.5         # stop = 1.5 ATR from entry
    target_atr_multiple: float = 3.0       # target = 3 ATR from entry
    require_close_above: bool = True       # close above level, not just wick
    bollinger_period: int = 20
    bollinger_std: float = 2.0


@dataclass
class MomentumConfig:
    fast_ema: int = 9
    slow_ema: int = 21
    rsi_period: int = 14
    rsi_trend_threshold: float = 55        # RSI > 55 confirms uptrend
    rsi_trend_threshold_short: float = 45  # RSI < 45 confirms downtrend
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    stop_atr_multiple: float = 2.0
    target_atr_multiple: float = 4.0
    roc_period: int = 10                   # rate of change lookback
    trend_ma_period: int = 50              # 50-period MA for trend filter


@dataclass
class MeanReversionConfig:
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    vwap_deviation_pct: float = 0.015      # 1.5% from VWAP
    atr_period: int = 14
    stop_atr_multiple: float = 1.5
    target_atr_multiple: float = 2.0       # tighter targets for MR
    require_rejection_candle: bool = True   # need wick rejection at level
    lookback_range: int = 50               # bars to check if range-bound
    range_atr_threshold: float = 0.5       # range width < 0.5x avg range = ranging


@dataclass
class BloombergConfig:
    host: str = "localhost"
    port: int = 8194
    default_ticker: str = "ESA Index"
    fields: list = field(default_factory=lambda: [
        "PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "VOLUME"
    ])
    # Additional fields for enrichment
    enrichment_fields: list = field(default_factory=lambda: [
        "IVOL_MID",                  # implied vol
        "OPEN_INT",                  # open interest
        "EQY_BETA",                  # beta
        "CUR_MKT_CAP",              # market cap (equities)
        "HIGH_52WEEK", "LOW_52WEEK", # 52-week range
    ])
    # COT data tickers (Commitment of Traders)
    cot_tickers: dict = field(default_factory=lambda: {
        "ES": "CFTCES Index",        # S&P 500 COT
        "NQ": "CFTCNQ Index",        # Nasdaq COT
        "CL": "CFTCCL Index",        # Crude Oil COT
        "GC": "CFTCGC Index",        # Gold COT
    })


@dataclass
class IBConfig:
    host: str = "127.0.0.1"
    port: int = 7497                       # 7497=TWS paper, 7496=TWS live, 4002=gateway paper
    client_id: int = 1
    timeout: int = 60
    # CME contract specs
    contracts: dict = field(default_factory=lambda: {
        "ES":  {"exchange": "CME",   "sec_type": "FUT", "multiplier": 50,   "tick_size": 0.25, "tick_value": 12.50},
        "MES": {"exchange": "CME",   "sec_type": "FUT", "multiplier": 5,    "tick_size": 0.25, "tick_value": 1.25},
        "NQ":  {"exchange": "CME",   "sec_type": "FUT", "multiplier": 20,   "tick_size": 0.25, "tick_value": 5.00},
        "MNQ": {"exchange": "CME",   "sec_type": "FUT", "multiplier": 2,    "tick_size": 0.25, "tick_value": 0.50},
        "CL":  {"exchange": "NYMEX", "sec_type": "FUT", "multiplier": 1000, "tick_size": 0.01, "tick_value": 10.00},
        "GC":  {"exchange": "COMEX", "sec_type": "FUT", "multiplier": 100,  "tick_size": 0.10, "tick_value": 10.00},
        "ZN":  {"exchange": "CBOT",  "sec_type": "FUT", "multiplier": 1000, "tick_size": 1/64, "tick_value": 15.625},
    })


@dataclass
class DataConfig:
    start_date: str = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    end_date: str = datetime.now().strftime("%Y-%m-%d")
    timeframe: str = "1h"                  # 1m, 5m, 15m, 1h, 4h, 1d
    min_bars_required: int = 200           # need enough history for indicators


# Master config
ACCOUNT = AccountConfig()
BREAKOUT = BreakoutConfig()
MOMENTUM = MomentumConfig()
MEAN_REVERSION = MeanReversionConfig()
BLOOMBERG = BloombergConfig()
IB = IBConfig()
DATA = DataConfig()
