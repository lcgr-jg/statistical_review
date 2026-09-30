"""
Base strategy class that all strategies inherit from.
Handles the backtest loop, trade execution simulation, and result collection.
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ACCOUNT, IB
from utils.risk import TradeSetup, SizedTrade, RiskManager, size_position


@dataclass
class TradeResult:
    entry_time: str
    exit_time: str
    instrument: str
    strategy: str
    direction: str
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    position_size: int
    pnl: float
    r_multiple: float
    exit_reason: str       # "target", "stop", "trailing_stop", "end_of_data"
    bars_held: int
    fees: float


class BaseStrategy(ABC):
    """
    Abstract base class for all strategies.
    Subclasses must implement:
        - compute_indicators(df) -> df
        - check_entry(df, i) -> Optional[TradeSetup]
        - check_exit(df, i, trade) -> Optional[tuple[float, str]]
    """

    def __init__(self, instrument: str = "ES", config=None):
        self.instrument = instrument
        self.config = config
        self.risk_manager = RiskManager()
        self.results: list[TradeResult] = []
        self.open_trade: Optional[SizedTrade] = None
        self.entry_bar: int = 0

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add strategy-specific indicators to the dataframe."""
        pass

    @abstractmethod
    def check_entry(self, df: pd.DataFrame, i: int) -> Optional[TradeSetup]:
        """
        Check if bar i triggers an entry signal.
        Return a TradeSetup if yes, None if no.
        IMPORTANT: Use data up to and including bar i only (no lookahead).
        """
        pass

    def check_exit(self, df: pd.DataFrame, i: int,
                   trade: SizedTrade) -> Optional[tuple[float, str]]:
        """
        Check if bar i triggers an exit.
        Default: check stop loss and target hit using bar's high/low.
        Override in subclass for custom exits (trailing stops, etc.)

        Returns: (exit_price, reason) or None
        """
        bar = df.iloc[i]

        if trade.direction == "long":
            # Stop hit?
            if bar["low"] <= trade.stop_price:
                return (trade.stop_price, "stop")
            # Target hit?
            if bar["high"] >= trade.target_price:
                return (trade.target_price, "target")

        elif trade.direction == "short":
            if bar["high"] >= trade.stop_price:
                return (trade.stop_price, "stop")
            if bar["low"] <= trade.target_price:
                return (trade.target_price, "target")

        return None

    def _calculate_pnl(self, trade: SizedTrade, exit_price: float) -> float:
        """Calculate P&L including fees and slippage."""
        specs = IB.contracts.get(self.instrument, {})
        multiplier = specs.get("multiplier", 1)
        tick_size = specs.get("tick_size", 0.01)
        tick_value = specs.get("tick_value", tick_size * multiplier)

        if trade.direction == "long":
            price_diff = exit_price - trade.entry_price
        else:
            price_diff = trade.entry_price - exit_price

        ticks = price_diff / tick_size if tick_size > 0 else 0
        gross_pnl = ticks * tick_value * trade.position_size

        # Fees: commission both sides + slippage both sides
        commission = ACCOUNT.commission_per_side * 2 * trade.position_size
        slippage = ACCOUNT.slippage_ticks * tick_value * 2 * trade.position_size
        fees = commission + slippage

        return gross_pnl - fees, fees

    def _calculate_r_multiple(self, trade: SizedTrade, pnl: float) -> float:
        """How many R did this trade make? 1R = initial risk amount."""
        if trade.dollar_risk > 0:
            return pnl / trade.dollar_risk
        return 0

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the backtest on the given data.
        Returns a DataFrame of trade results.
        """
        print(f"\n{'='*50}")
        print(f"Running {self.name} on {self.instrument}")
        print(f"{'='*50}")
        print(f"Data: {len(df)} bars from {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")

        # Compute indicators
        df = self.compute_indicators(df.copy())

        # Need enough bars for indicators to warm up
        start_bar = 50
        current_date = None

        for i in range(start_bar, len(df)):
            bar = df.iloc[i]

            # Reset daily limits on new day
            bar_date = bar.get("date", None)
            if bar_date and bar_date != current_date:
                self.risk_manager.reset_daily()
                current_date = bar_date

            # Check exit first (if we have an open position)
            if self.open_trade is not None:
                exit_result = self.check_exit(df, i, self.open_trade)
                if exit_result:
                    exit_price, reason = exit_result
                    pnl, fees = self._calculate_pnl(self.open_trade, exit_price)
                    r_mult = self._calculate_r_multiple(self.open_trade, pnl)

                    self.results.append(TradeResult(
                        entry_time=str(df.iloc[self.entry_bar]["datetime"]),
                        exit_time=str(bar["datetime"]),
                        instrument=self.instrument,
                        strategy=self.name,
                        direction=self.open_trade.direction,
                        entry_price=self.open_trade.entry_price,
                        exit_price=exit_price,
                        stop_price=self.open_trade.stop_price,
                        target_price=self.open_trade.target_price,
                        position_size=self.open_trade.position_size,
                        pnl=pnl,
                        r_multiple=r_mult,
                        exit_reason=reason,
                        bars_held=i - self.entry_bar,
                        fees=fees,
                    ))

                    self.risk_manager.close_trade(self.open_trade, pnl)
                    self.open_trade = None

            # Check entry (only if flat)
            if self.open_trade is None:
                setup = self.check_entry(df, i)
                if setup:
                    sized = size_position(setup, self.risk_manager.balance)
                    if sized.position_size > 0:
                        can_trade, reason = self.risk_manager.can_trade(sized)
                        if can_trade:
                            self.risk_manager.open_trade(sized)
                            self.open_trade = sized
                            self.entry_bar = i

        # Close any remaining position at last bar
        if self.open_trade is not None:
            last_price = df.iloc[-1]["close"]
            pnl, fees = self._calculate_pnl(self.open_trade, last_price)
            r_mult = self._calculate_r_multiple(self.open_trade, pnl)
            self.results.append(TradeResult(
                entry_time=str(df.iloc[self.entry_bar]["datetime"]),
                exit_time=str(df.iloc[-1]["datetime"]),
                instrument=self.instrument,
                strategy=self.name,
                direction=self.open_trade.direction,
                entry_price=self.open_trade.entry_price,
                exit_price=last_price,
                stop_price=self.open_trade.stop_price,
                target_price=self.open_trade.target_price,
                position_size=self.open_trade.position_size,
                pnl=pnl,
                r_multiple=r_mult,
                exit_reason="end_of_data",
                bars_held=len(df) - 1 - self.entry_bar,
                fees=fees,
            ))
            self.risk_manager.close_trade(self.open_trade, pnl)
            self.open_trade = None

        results_df = pd.DataFrame([vars(r) for r in self.results])
        print(f"Completed: {len(self.results)} trades")
        print(f"Final balance: ${self.risk_manager.balance:,.2f}")
        return results_df
