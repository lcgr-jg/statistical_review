"""
Interactive Brokers Data Pipeline
=================================
Pulls historical data from IB TWS or Gateway via ib_insync.

Requirements:
    - IB TWS or IB Gateway running (paper or live)
    - pip install ib_insync

Usage:
    from data.ib_pipeline import IBPipeline
    ib = IBPipeline()
    df = ib.get_historical("ES", bar_size="1 hour", duration="6 M")
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import IB, DATA


class IBPipeline:
    """Pull data from Interactive Brokers TWS/Gateway."""

    def __init__(self, host=None, port=None, client_id=None):
        self.host = host or IB.host
        self.port = port or IB.port
        self.client_id = client_id or IB.client_id
        self.ib = None

    def connect(self):
        try:
            from ib_insync import IB as IBConnection
        except ImportError:
            raise ImportError("ib_insync not installed. Run: pip install ib_insync")

        self.ib = IBConnection()
        self.ib.connect(self.host, self.port, clientId=self.client_id)
        print(f"Connected to IB on {self.host}:{self.port}")

    def _get_contract(self, symbol: str):
        """Build a futures contract object for the given symbol."""
        from ib_insync import Future
        specs = IB.contracts.get(symbol)
        if not specs:
            raise ValueError(f"Unknown symbol: {symbol}. Add it to config.IB.contracts")
        contract = Future(
            symbol=symbol,
            exchange=specs["exchange"],
            currency="USD",
        )
        # Qualify to get the front-month contract
        qualified = self.ib.qualifyContracts(contract)
        if qualified:
            return qualified[0]
        # Fallback: try with explicit last trade date (front month)
        contracts = self.ib.reqContractDetails(contract)
        if contracts:
            return contracts[0].contract
        raise ValueError(f"Could not qualify contract for {symbol}")

    def get_historical(self, symbol: str, bar_size: str = "1 hour",
                       duration: str = "6 M",
                       end_date: str = "",
                       what_to_show: str = "TRADES") -> pd.DataFrame:
        """
        Pull historical bars from IB.

        Args:
            symbol: Instrument (e.g., "ES", "NQ", "CL", "GC")
            bar_size: "1 min", "5 mins", "15 mins", "30 mins",
                      "1 hour", "4 hours", "1 day", "1 week"
            duration: "60 S", "120 S", "1 D", "1 W", "1 M", "6 M", "1 Y"
            end_date: "" for now, or "YYYYMMDD HH:MM:SS"
            what_to_show: "TRADES", "MIDPOINT", "BID", "ASK"

        Returns:
            DataFrame with: datetime, open, high, low, close, volume, date
        """
        if not self.ib:
            self.connect()

        contract = self._get_contract(symbol)
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime=end_date,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=True,           # regular trading hours only
            formatDate=1,
        )

        if not bars:
            print(f"Warning: No data returned for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame([{
            "datetime": b.date,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        } for b in bars])

        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.date
        df = df.sort_values("datetime").reset_index(drop=True)
        print(f"Loaded {len(df)} bars for {symbol} ({bar_size})")
        return df

    def get_market_snapshot(self, symbol: str) -> dict:
        """Get current market data snapshot."""
        if not self.ib:
            self.connect()

        contract = self._get_contract(symbol)
        self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(2)

        ticker = self.ib.ticker(contract)
        return {
            "last": ticker.last,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "volume": ticker.volume,
            "high": ticker.high,
            "low": ticker.low,
            "open": ticker.open,
        }

    def disconnect(self):
        if self.ib:
            self.ib.disconnect()


# ============================================================
# TIMEFRAME MAPPING
# ============================================================
TIMEFRAME_MAP = {
    "1m":  ("1 min",   "2 D"),
    "5m":  ("5 mins",  "1 W"),
    "15m": ("15 mins", "2 W"),
    "30m": ("30 mins", "1 M"),
    "1h":  ("1 hour",  "6 M"),
    "4h":  ("4 hours", "1 Y"),
    "1d":  ("1 day",   "2 Y"),
}


def get_ib_data(symbol: str, timeframe: str = None) -> pd.DataFrame:
    """Convenience function: connect, pull, disconnect."""
    tf = timeframe or DATA.timeframe
    bar_size, duration = TIMEFRAME_MAP.get(tf, ("1 hour", "6 M"))

    pipeline = IBPipeline()
    try:
        df = pipeline.get_historical(symbol, bar_size=bar_size, duration=duration)
    finally:
        pipeline.disconnect()
    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="MES", help="IB symbol")
    parser.add_argument("--timeframe", default="1h", help="Timeframe: 1m,5m,15m,1h,4h,1d")
    parser.add_argument("--output", default=None, help="Output CSV path")
    args = parser.parse_args()

    df = get_ib_data(args.symbol, args.timeframe)
    if not df.empty:
        out = args.output or f"data/{args.symbol}_{args.timeframe}.csv"
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} bars to {out}")
