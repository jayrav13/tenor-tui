from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# US market hours in minutes from midnight ET
PRE_MARKET_OPEN = 4 * 60  # 4:00 AM
REGULAR_OPEN = 9 * 60 + 30  # 9:30 AM
REGULAR_CLOSE = 16 * 60  # 4:00 PM
AFTER_HOURS_CLOSE = 20 * 60  # 8:00 PM


class MarketState(Enum):
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"

    @property
    def display_name(self) -> str:
        return {
            MarketState.PRE_MARKET: "Pre-Market",
            MarketState.REGULAR: "Market Open",
            MarketState.AFTER_HOURS: "After-Hours",
            MarketState.CLOSED: "Market Closed",
        }[self]


def _to_et(dt: datetime) -> datetime:
    """Convert a datetime to ET. Treat naive datetimes as ET."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ET)
    return dt.astimezone(ET)


def get_market_state(dt: datetime | None = None) -> MarketState:
    """Determine US stock market state from time."""
    if dt is None:
        dt = datetime.now(ET)
    else:
        dt = _to_et(dt)

    if dt.weekday() >= 5:  # Saturday=5, Sunday=6
        return MarketState.CLOSED

    mins = dt.hour * 60 + dt.minute

    if mins < PRE_MARKET_OPEN:
        return MarketState.CLOSED
    elif mins < REGULAR_OPEN:
        return MarketState.PRE_MARKET
    elif mins < REGULAR_CLOSE:
        return MarketState.REGULAR
    elif mins < AFTER_HOURS_CLOSE:
        return MarketState.AFTER_HOURS
    else:
        return MarketState.CLOSED


def time_to_next_state(dt: datetime | None = None) -> int:
    """Return minutes until the next market state transition."""
    if dt is None:
        dt = datetime.now(ET)
    else:
        dt = _to_et(dt)

    mins = dt.hour * 60 + dt.minute
    state = get_market_state(dt)

    if state == MarketState.PRE_MARKET:
        return REGULAR_OPEN - mins
    elif state == MarketState.REGULAR:
        return REGULAR_CLOSE - mins
    elif state == MarketState.AFTER_HOURS:
        return AFTER_HOURS_CLOSE - mins
    else:
        # Closed — return minutes to next pre-market (4 AM)
        if dt.weekday() >= 5:  # Weekend
            days_until_monday = 7 - dt.weekday()
            return (days_until_monday * 24 * 60) - mins + PRE_MARKET_OPEN
        elif mins >= AFTER_HOURS_CLOSE:
            # After 8 PM, next day pre-market
            return (24 * 60 - mins) + PRE_MARKET_OPEN
        else:
            # Before 4 AM
            return PRE_MARKET_OPEN - mins
