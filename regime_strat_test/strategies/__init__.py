from .calendar_spread import CalendarSpreadStrategy
from .cash_and_carry import CashAndCarryStrategy
from .crack_mr import CrackMeanReversionStrategy
from .extras import CrackSkewStrategy, SeasonalInventoryStrategy
from .gex_fade import GEXFadeStrategy
from .vol_calendar import VolCalendarStrategy

STRATEGY_REGISTRY = {
    "cash_and_carry": CashAndCarryStrategy,
    "calendar_spread": CalendarSpreadStrategy,
    "crack_mr": CrackMeanReversionStrategy,
    "vol_calendar": VolCalendarStrategy,
    "gex_fade": GEXFadeStrategy,
    "seasonal_inventory": SeasonalInventoryStrategy,
    "crack_skew": CrackSkewStrategy,
}

__all__ = list(STRATEGY_REGISTRY) + ["STRATEGY_REGISTRY"]
