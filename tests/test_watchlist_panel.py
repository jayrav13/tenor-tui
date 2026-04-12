# tests/test_watchlist_panel.py
import pytest
from datetime import date, timedelta

from tenortui.models import Quote
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_panel import WatchlistPanel


@pytest.fixture
def sample_watchlist_data():
    return WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[
                    WatchlistItem(type="equity", symbol="AAPL"),
                    WatchlistItem(
                        type="option",
                        symbol="AAPL",
                        strike=180.0,
                        option_type="put",
                        expiration="2026-04-17",
                    ),
                    WatchlistItem(type="equity", symbol="MSFT"),
                ],
            ),
            Watchlist(name="Tech", items=[]),
        ],
        active_index=0,
    )


@pytest.fixture
def sample_equity_quotes():
    return [
        Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
        ),
        Quote(
            symbol="MSFT",
            name="Microsoft Corp.",
            price=415.10,
            change=-2.30,
            change_percent=-0.55,
            volume=32_100_000,
        ),
    ]


class TestWatchlistPanelGrouping:
    def test_groups_by_underlying(self, sample_watchlist_data):
        panel = WatchlistPanel()
        groups = panel._build_display_groups(sample_watchlist_data.watchlists[0].items)
        # AAPL group: 1 equity + 1 option, MSFT group: 1 equity
        assert len(groups) == 2
        assert groups[0][0] == "AAPL"
        assert len(groups[0][1]) == 2  # equity + option
        assert groups[1][0] == "MSFT"
        assert len(groups[1][1]) == 1  # equity only

    def test_option_only_group(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(
                type="option",
                symbol="GOOG",
                strike=150.0,
                option_type="call",
                expiration="2026-04-17",
            )
        ]
        groups = panel._build_display_groups(items)
        assert len(groups) == 1
        assert groups[0][0] == "GOOG"


class TestWatchlistPanelDTE:
    def test_dte_calculation(self):
        panel = WatchlistPanel()
        future = (date.today() + timedelta(days=30)).isoformat()
        assert panel._calculate_dte(future) == 30

    def test_dte_warning_threshold(self):
        panel = WatchlistPanel()
        near_expiry = (date.today() + timedelta(days=5)).isoformat()
        assert panel._calculate_dte(near_expiry) <= 7


class TestWatchlistPanelRemove:
    def test_remove_returns_item(self, sample_watchlist_data):
        panel = WatchlistPanel()
        panel._watchlist_data = sample_watchlist_data
        panel._active_index = 0
        # Simulate selected flat index 0 -> first item (AAPL equity)
        removed = panel._get_item_at_flat_index(0)
        assert removed is not None
        assert removed.symbol == "AAPL"
        assert removed.type == "equity"

    def test_flat_index_maps_to_option(self, sample_watchlist_data):
        panel = WatchlistPanel()
        panel._watchlist_data = sample_watchlist_data
        panel._active_index = 0
        # Flat index 1 -> AAPL option
        item = panel._get_item_at_flat_index(1)
        assert item is not None
        assert item.type == "option"
        assert item.strike == 180.0
