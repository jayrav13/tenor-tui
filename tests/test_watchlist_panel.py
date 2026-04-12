# tests/test_watchlist_panel.py
import pytest
from datetime import date, timedelta

from textual.app import App, ComposeResult
from textual.widgets import Button, Label, ListView, Static

from tenortui.models import OptionContract, Quote
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_panel import WatchlistPanel


# --- Helpers ---


class PanelApp(App):
    """Test app that mounts a WatchlistPanel."""

    def __init__(self):
        super().__init__()
        self.messages = []

    def compose(self) -> ComposeResult:
        yield WatchlistPanel()

    def on_watchlist_panel_ticker_selected(self, event):
        self.messages.append(("ticker_selected", event.symbol))

    def on_watchlist_panel_watchlist_changed(self, event):
        self.messages.append(("watchlist_changed", event.index))


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


# --- Grouping tests (non-async, from original) ---


class TestWatchlistPanelGrouping:
    def test_groups_by_underlying(self, sample_watchlist_data):
        panel = WatchlistPanel()
        groups = panel._build_display_groups(sample_watchlist_data.watchlists[0].items)
        assert len(groups) == 2
        assert groups[0][0] == "AAPL"
        assert len(groups[0][1]) == 2
        assert groups[1][0] == "MSFT"
        assert len(groups[1][1]) == 1

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
        removed = panel._get_item_at_flat_index(0)
        assert removed is not None
        assert removed.symbol == "AAPL"
        assert removed.type == "equity"

    def test_flat_index_maps_to_option(self, sample_watchlist_data):
        panel = WatchlistPanel()
        panel._watchlist_data = sample_watchlist_data
        panel._active_index = 0
        item = panel._get_item_at_flat_index(1)
        assert item is not None
        assert item.type == "option"
        assert item.strike == 180.0


class TestWatchlistPanelSorting:
    def test_sort_by_symbol(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="GOOG"),
        ]
        groups = panel._build_display_groups(items, sort_key="symbol")
        assert [g[0] for g in groups] == ["AAPL", "GOOG", "MSFT"]

    def test_sort_by_price(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                name="Apple",
                price=213.0,
                change=0,
                change_percent=0,
                volume=0,
            ),
            "MSFT": Quote(
                symbol="MSFT",
                name="Microsoft",
                price=415.0,
                change=0,
                change_percent=0,
                volume=0,
            ),
        }
        items = [
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="MSFT"),
        ]
        groups = panel._build_display_groups(items, sort_key="price")
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]

    def test_sort_by_change(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                name="Apple",
                price=213.0,
                change=5.0,
                change_percent=2.4,
                volume=0,
            ),
            "MSFT": Quote(
                symbol="MSFT",
                name="Microsoft",
                price=415.0,
                change=-2.0,
                change_percent=-0.5,
                volume=0,
            ),
        }
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
        ]
        groups = panel._build_display_groups(items, sort_key="change")
        assert [g[0] for g in groups] == ["AAPL", "MSFT"]

    def test_sort_by_volume(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                name="Apple",
                price=213.0,
                change=0,
                change_percent=0,
                volume=100,
            ),
            "MSFT": Quote(
                symbol="MSFT",
                name="Microsoft",
                price=415.0,
                change=0,
                change_percent=0,
                volume=500,
            ),
        }
        items = [
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="MSFT"),
        ]
        groups = panel._build_display_groups(items, sort_key="volume")
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]

    def test_default_sort_preserves_insertion_order(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
        ]
        groups = panel._build_display_groups(items)
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]


# --- Async widget tests ---


@pytest.mark.asyncio
async def test_panel_set_watchlists_rebuilds_tabs(sample_watchlist_data):
    """set_watchlists populates tab buttons and list items."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        # Tab bar should have 2 buttons
        buttons = panel.query(".wl-tab")
        assert len(buttons) == 2
        labels = [b.label for b in buttons]
        assert "Default" in str(labels[0])
        assert "Tech" in str(labels[1])


@pytest.mark.asyncio
async def test_panel_set_watchlists_shows_items(sample_watchlist_data):
    """set_watchlists shows the items for the active watchlist."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        # Should have 3 items: AAPL equity, AAPL option, MSFT equity
        items = list(lv.query("ListItem"))
        assert len(items) == 3


@pytest.mark.asyncio
async def test_panel_empty_watchlist_shows_empty_message(sample_watchlist_data):
    """Switching to an empty watchlist shows the empty message."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        # Set active to the empty "Tech" watchlist
        sample_watchlist_data.active_index = 1
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        empty = panel.query_one("#wl-empty", Static)
        lv = panel.query_one(ListView)
        assert empty.display is True
        assert lv.display is False


@pytest.mark.asyncio
async def test_panel_update_equity_quotes(sample_watchlist_data, sample_equity_quotes):
    """update_equity_quotes populates price info in the list."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        panel.update_equity_quotes(sample_equity_quotes)
        await pilot.pause()

        # After updating, the equity rows should show price info
        lv = panel.query_one(ListView)
        first_label = lv.children[0].query_one(Label).render().plain
        assert "AAPL" in first_label
        assert "213.25" in first_label


@pytest.mark.asyncio
async def test_panel_update_contract_quotes(sample_watchlist_data):
    """update_contract_quotes fills in option bid/ask info."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        contract = OptionContract(
            contract_symbol="AAPL260417P00180000",
            option_type="put",
            strike=180.0,
            bid=2.50,
            ask=2.80,
            last_price=2.65,
            volume=500,
            open_interest=1200,
            implied_volatility=0.30,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        panel.update_contract_quotes({("AAPL", "2026-04-17"): [contract]})
        await pilot.pause()

        # The option row should show bid/ask
        lv = panel.query_one(ListView)
        option_label = lv.children[1].query_one(Label).render().plain
        assert "2.50" in option_label
        assert "2.80" in option_label


@pytest.mark.asyncio
async def test_panel_tab_switch(sample_watchlist_data):
    """on_button_pressed with a wl-tab button switches the active watchlist."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        assert panel._active_index == 0

        # Create a mock button event to exercise on_button_pressed code path.
        # Directly calling _rebuild_tabs in tests causes DuplicateIds because
        # remove_children() is async but _rebuild_tabs is sync.
        # We monkeypatch _rebuild_tabs and _rebuild_list to verify the handler
        # updates state correctly.
        rebuild_tabs_called = []
        rebuild_list_called = []
        orig_rebuild_tabs = panel._rebuild_tabs
        orig_rebuild_list = panel._rebuild_list
        panel._rebuild_tabs = lambda: rebuild_tabs_called.append(True)
        panel._rebuild_list = lambda: rebuild_list_called.append(True)

        tech_btn = panel.query_one("#wl-tab-1", Button)
        panel.on_button_pressed(Button.Pressed(tech_btn))
        await pilot.pause()

        assert panel._active_index == 1
        assert sample_watchlist_data.active_index == 1
        assert len(rebuild_tabs_called) == 1
        assert len(rebuild_list_called) == 1
        # Should have posted a WatchlistChanged message
        assert ("watchlist_changed", 1) in app.messages

        # Restore
        panel._rebuild_tabs = orig_rebuild_tabs
        panel._rebuild_list = orig_rebuild_list


@pytest.mark.asyncio
async def test_panel_ticker_selected_on_equity(sample_watchlist_data):
    """Selecting an equity item posts TickerSelected."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        lv.index = 0  # AAPL equity
        await pilot.press("enter")
        await pilot.pause()

        assert ("ticker_selected", "AAPL") in app.messages


@pytest.mark.asyncio
async def test_panel_option_selection_no_ticker_event(sample_watchlist_data):
    """Selecting an option item does not post TickerSelected."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        lv.index = 1  # AAPL option
        await pilot.press("enter")
        await pilot.pause()

        # No ticker_selected should be in messages
        assert all(m[0] != "ticker_selected" for m in app.messages)


@pytest.mark.asyncio
async def test_panel_cycle_sort(sample_watchlist_data, sample_equity_quotes):
    """cycle_sort cycles through sort keys and rebuilds the list."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        panel.update_equity_quotes(sample_equity_quotes)
        await pilot.pause()

        # Default is None
        assert panel._sort_key is None

        result = panel.cycle_sort()
        assert result == "symbol"
        await pilot.pause()

        result = panel.cycle_sort()
        assert result == "price"
        await pilot.pause()

        result = panel.cycle_sort()
        assert result == "change"
        await pilot.pause()

        result = panel.cycle_sort()
        assert result == "volume"
        await pilot.pause()

        # Wraps back to None
        result = panel.cycle_sort()
        assert result is None


@pytest.mark.asyncio
async def test_panel_get_selected_item(sample_watchlist_data):
    """get_selected_item returns the item at the current ListView index."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        lv.index = 2  # MSFT equity (third flat item)
        item = panel.get_selected_item()
        assert item is not None
        assert item.symbol == "MSFT"
        assert item.type == "equity"


@pytest.mark.asyncio
async def test_panel_get_selected_item_none_index(sample_watchlist_data):
    """get_selected_item returns None when no selection."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        lv.index = None
        item = panel.get_selected_item()
        assert item is None


@pytest.mark.asyncio
async def test_panel_contract_without_quote(sample_watchlist_data):
    """Option item without a matching contract quote shows basic info."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        # Second item is the AAPL put option (no contract quotes loaded)
        option_label = lv.children[1].query_one(Label).render().plain
        assert "180P" in option_label
        assert "DTE:" in option_label


@pytest.mark.asyncio
async def test_panel_equity_without_quote(sample_watchlist_data):
    """Equity item without a quote shows just the symbol."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        first_label = lv.children[0].query_one(Label).render().plain
        assert "AAPL" in first_label


@pytest.mark.asyncio
async def test_panel_find_contract_quote_no_expiration():
    """_find_contract_quote returns None for item with no expiration."""
    panel = WatchlistPanel()
    item = WatchlistItem(type="option", symbol="AAPL", strike=180.0, option_type="put")
    assert panel._find_contract_quote(item) is None


@pytest.mark.asyncio
async def test_panel_find_contract_quote_no_match():
    """_find_contract_quote returns None when no matching contract exists."""
    panel = WatchlistPanel()
    item = WatchlistItem(
        type="option",
        symbol="AAPL",
        strike=180.0,
        option_type="put",
        expiration="2026-04-17",
    )
    # Add a contract with different strike
    other = OptionContract(
        contract_symbol="AAPL260417P00200000",
        option_type="put",
        strike=200.0,
        bid=5.0,
        ask=5.5,
        last_price=5.25,
        volume=100,
        open_interest=500,
        implied_volatility=0.30,
        delta=None,
        gamma=None,
        theta=None,
        vega=None,
        rho=None,
    )
    panel._contract_quotes[("AAPL", "2026-04-17")] = [other]
    assert panel._find_contract_quote(item) is None


@pytest.mark.asyncio
async def test_panel_call_option_display():
    """Call options display C suffix instead of P."""
    data = WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[
                    WatchlistItem(
                        type="option",
                        symbol="GOOG",
                        strike=150.0,
                        option_type="call",
                        expiration="2026-04-17",
                    ),
                ],
            ),
        ],
        active_index=0,
    )
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        label = lv.children[0].query_one(Label).render().plain
        assert "150C" in label


@pytest.mark.asyncio
async def test_panel_dte_warning_class():
    """Options expiring within 7 days get the warning class."""
    near_exp = (date.today() + timedelta(days=3)).isoformat()
    data = WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[
                    WatchlistItem(
                        type="option",
                        symbol="AAPL",
                        strike=180.0,
                        option_type="put",
                        expiration=near_exp,
                    ),
                ],
            ),
        ],
        active_index=0,
    )
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(data)
        await pilot.pause()

        lv = panel.query_one(ListView)
        label = lv.children[0].query_one(Label)
        assert label.has_class("wl-contract-warning")


@pytest.mark.asyncio
async def test_panel_tab_active_class(sample_watchlist_data):
    """Active tab gets the 'active' class on initial render."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        tab0 = panel.query_one("#wl-tab-0", Button)
        tab1 = panel.query_one("#wl-tab-1", Button)
        assert tab0.has_class("active")
        assert not tab1.has_class("active")


@pytest.mark.asyncio
async def test_panel_on_button_pressed_ignores_non_tab(sample_watchlist_data):
    """on_button_pressed ignores buttons without wl-tab- prefix."""
    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(WatchlistPanel)
        panel.set_watchlists(sample_watchlist_data)
        await pilot.pause()

        # Create a button with a different ID
        other_btn = Button("Other", id="something-else")
        panel.on_button_pressed(Button.Pressed(other_btn))
        await pilot.pause()

        # Active index should not change
        assert panel._active_index == 0
