"""
Position sizing and risk management.
Mirrors the logic from the Excel Position Sizer sheet.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from config import ACCOUNT, IB


@dataclass
class TradeSetup:
    instrument: str
    direction: str       # "long" or "short"
    entry_price: float
    stop_price: float
    target_price: float
    signal_bar_index: int
    strategy: str
    notes: str = ""


@dataclass
class SizedTrade(TradeSetup):
    position_size: int = 0
    dollar_risk: float = 0.0
    dollar_target: float = 0.0
    risk_reward: float = 0.0
    pct_of_account: float = 0.0


def size_position(setup: TradeSetup, account_balance: float = None,
                  risk_pct: float = None) -> SizedTrade:
    """
    Calculate position size based on fixed-risk model.
    Risk per trade = account_balance * risk_pct
    Position size = risk_per_trade / (entry - stop) per contract
    """
    bal = account_balance or ACCOUNT.balance
    rpct = risk_pct or ACCOUNT.risk_per_trade_pct
    max_risk = bal * rpct

    # Get contract specs
    specs = IB.contracts.get(setup.instrument, {})
    multiplier = specs.get("multiplier", 1)
    tick_size = specs.get("tick_size", 0.01)
    tick_value = specs.get("tick_value", tick_size * multiplier)

    # Risk per contract
    price_risk = abs(setup.entry_price - setup.stop_price)
    ticks_risk = price_risk / tick_size if tick_size > 0 else 0
    dollar_risk_per_contract = ticks_risk * tick_value

    if dollar_risk_per_contract <= 0:
        return SizedTrade(**vars(setup))

    # Size and cap at max risk
    raw_size = max_risk / dollar_risk_per_contract
    position_size = int(np.floor(raw_size))
    position_size = max(position_size, 0)

    # Reward per contract
    price_reward = abs(setup.target_price - setup.entry_price)
    ticks_reward = price_reward / tick_size if tick_size > 0 else 0
    dollar_reward_per_contract = ticks_reward * tick_value

    rr = dollar_reward_per_contract / dollar_risk_per_contract if dollar_risk_per_contract > 0 else 0

    return SizedTrade(
        instrument=setup.instrument,
        direction=setup.direction,
        entry_price=setup.entry_price,
        stop_price=setup.stop_price,
        target_price=setup.target_price,
        signal_bar_index=setup.signal_bar_index,
        strategy=setup.strategy,
        notes=setup.notes,
        position_size=position_size,
        dollar_risk=position_size * dollar_risk_per_contract,
        dollar_target=position_size * dollar_reward_per_contract,
        risk_reward=rr,
        pct_of_account=(position_size * dollar_risk_per_contract) / bal if bal > 0 else 0,
    )


class RiskManager:
    """
    Tracks open risk, daily P&L, and enforces limits.
    Simulates what an institutional risk system does automatically.
    """

    def __init__(self, config=None):
        self.config = config or ACCOUNT
        self.balance = self.config.balance
        self.daily_pnl = 0.0
        self.open_positions = []
        self.total_open_risk = 0.0
        self.trade_count_today = 0
        self.daily_loss_limit_hit = False

    def can_trade(self, sized_trade: SizedTrade) -> tuple[bool, str]:
        """Check if a new trade passes all risk checks."""
        if self.daily_loss_limit_hit:
            return False, "Daily loss limit already hit"

        if abs(self.daily_pnl) >= self.config.max_daily_loss:
            self.daily_loss_limit_hit = True
            return False, f"Daily loss limit reached: ${self.daily_pnl:.2f}"

        if len(self.open_positions) >= self.config.max_open_positions:
            return False, f"Max open positions ({self.config.max_open_positions}) reached"

        new_total_risk = self.total_open_risk + sized_trade.dollar_risk
        max_portfolio_risk = self.balance * self.config.max_daily_loss_pct * 2
        if new_total_risk > max_portfolio_risk:
            return False, f"Portfolio risk limit: ${new_total_risk:.2f} > ${max_portfolio_risk:.2f}"

        if sized_trade.risk_reward < 1.0:
            return False, f"R:R too low: {sized_trade.risk_reward:.2f} (min 1.0)"

        return True, "OK"

    def open_trade(self, trade: SizedTrade):
        self.open_positions.append(trade)
        self.total_open_risk += trade.dollar_risk
        self.trade_count_today += 1

    def close_trade(self, trade: SizedTrade, pnl: float):
        if trade in self.open_positions:
            self.open_positions.remove(trade)
            self.total_open_risk -= trade.dollar_risk
        self.daily_pnl += pnl
        self.balance += pnl

        if self.daily_pnl <= -self.config.max_daily_loss:
            self.daily_loss_limit_hit = True

    def reset_daily(self):
        self.daily_pnl = 0.0
        self.trade_count_today = 0
        self.daily_loss_limit_hit = False

    def get_status(self) -> dict:
        return {
            "balance": self.balance,
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.open_positions),
            "total_open_risk": self.total_open_risk,
            "daily_loss_limit_hit": self.daily_loss_limit_hit,
        }
