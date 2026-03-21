"""Tests for market hours detection."""

from datetime import datetime
from zoneinfo import ZoneInfo

from tenortui.market_hours import MarketState, get_market_state, time_to_next_state

ET = ZoneInfo("America/New_York")


class TestGetMarketState:
    def test_regular_hours(self):
        """10:00 AM ET on a Monday is regular trading."""
        dt = datetime(2026, 3, 23, 10, 0, tzinfo=ET)  # Monday
        assert get_market_state(dt) == MarketState.REGULAR

    def test_regular_hours_open(self):
        """9:30 AM ET is the start of regular trading."""
        dt = datetime(2026, 3, 23, 9, 30, tzinfo=ET)
        assert get_market_state(dt) == MarketState.REGULAR

    def test_regular_hours_before_close(self):
        """3:59 PM ET is still regular trading."""
        dt = datetime(2026, 3, 23, 15, 59, tzinfo=ET)
        assert get_market_state(dt) == MarketState.REGULAR

    def test_pre_market(self):
        """7:00 AM ET on a Tuesday is pre-market."""
        dt = datetime(2026, 3, 24, 7, 0, tzinfo=ET)  # Tuesday
        assert get_market_state(dt) == MarketState.PRE_MARKET

    def test_pre_market_open(self):
        """4:00 AM ET is the start of pre-market."""
        dt = datetime(2026, 3, 23, 4, 0, tzinfo=ET)
        assert get_market_state(dt) == MarketState.PRE_MARKET

    def test_after_hours(self):
        """5:00 PM ET is after-hours."""
        dt = datetime(2026, 3, 23, 17, 0, tzinfo=ET)
        assert get_market_state(dt) == MarketState.AFTER_HOURS

    def test_after_hours_start(self):
        """4:00 PM ET is the start of after-hours."""
        dt = datetime(2026, 3, 23, 16, 0, tzinfo=ET)
        assert get_market_state(dt) == MarketState.AFTER_HOURS

    def test_closed_night(self):
        """11:00 PM ET is closed."""
        dt = datetime(2026, 3, 23, 23, 0, tzinfo=ET)
        assert get_market_state(dt) == MarketState.CLOSED

    def test_closed_early_morning(self):
        """3:00 AM ET is closed."""
        dt = datetime(2026, 3, 23, 3, 0, tzinfo=ET)
        assert get_market_state(dt) == MarketState.CLOSED

    def test_closed_weekend_saturday(self):
        """Saturday is closed regardless of time."""
        dt = datetime(2026, 3, 21, 10, 0, tzinfo=ET)  # Saturday
        assert get_market_state(dt) == MarketState.CLOSED

    def test_closed_weekend_sunday(self):
        """Sunday is closed regardless of time."""
        dt = datetime(2026, 3, 22, 10, 0, tzinfo=ET)  # Sunday
        assert get_market_state(dt) == MarketState.CLOSED

    def test_naive_datetime_treated_as_et(self):
        """Naive datetime is treated as ET."""
        dt = datetime(2026, 3, 23, 10, 0)  # No tzinfo, Monday
        assert get_market_state(dt) == MarketState.REGULAR

    def test_other_timezone_converted(self):
        """UTC datetime is correctly converted to ET."""
        # 2:00 PM UTC = 10:00 AM ET (during EDT)
        utc = ZoneInfo("UTC")
        dt = datetime(2026, 3, 23, 14, 0, tzinfo=utc)
        assert get_market_state(dt) == MarketState.REGULAR


class TestMarketStateDisplay:
    def test_regular_display(self):
        assert MarketState.REGULAR.display_name == "Market Open"

    def test_pre_market_display(self):
        assert MarketState.PRE_MARKET.display_name == "Pre-Market"

    def test_after_hours_display(self):
        assert MarketState.AFTER_HOURS.display_name == "After-Hours"

    def test_closed_display(self):
        assert MarketState.CLOSED.display_name == "Market Closed"


class TestTimeToNextState:
    def test_time_to_close_during_regular(self):
        """During regular hours, returns time to close (4 PM ET)."""
        dt = datetime(2026, 3, 23, 14, 0, tzinfo=ET)  # 2:00 PM
        minutes = time_to_next_state(dt)
        assert minutes == 120  # 2 hours to 4 PM

    def test_time_to_open_during_pre_market(self):
        """During pre-market, returns time to open (9:30 AM ET)."""
        dt = datetime(2026, 3, 23, 8, 0, tzinfo=ET)  # 8:00 AM
        minutes = time_to_next_state(dt)
        assert minutes == 90  # 1.5 hours to 9:30 AM

    def test_time_to_close_after_hours(self):
        """During after-hours, returns time to close (8 PM ET)."""
        dt = datetime(2026, 3, 23, 19, 0, tzinfo=ET)  # 7:00 PM
        minutes = time_to_next_state(dt)
        assert minutes == 60  # 1 hour to 8 PM
