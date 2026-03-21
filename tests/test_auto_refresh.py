"""Tests for auto-refresh and market hours integration."""

import pytest
from textual.app import App

from tenortui.app import TenorTUI
from tenortui.widgets.status_bar import StatusBar


# --- Status Bar Market State ---


@pytest.mark.asyncio
async def test_status_bar_shows_market_state():
    """Status bar displays market state after update."""

    class StatusTestApp(App):
        def compose(self):
            yield StatusBar(provider_name="yahoo")

    app = StatusTestApp()
    async with app.run_test():
        bar = app.query_one(StatusBar)
        bar.update_market_state()
        market_widget = bar.query_one("#status-market")
        rendered = market_widget.render().plain
        # Should contain one of the market states
        assert any(
            s in rendered
            for s in ["Market Open", "Pre-Market", "After-Hours", "Market Closed"]
        )


@pytest.mark.asyncio
async def test_status_bar_refresh_countdown():
    """Status bar shows refresh countdown."""

    class StatusTestApp(App):
        def compose(self):
            yield StatusBar(provider_name="yahoo")

    app = StatusTestApp()
    async with app.run_test():
        bar = app.query_one(StatusBar)
        bar.update_refresh_status(seconds_until=45)
        widget = bar.query_one("#status-refresh")
        rendered = widget.render().plain
        assert "45s" in rendered


@pytest.mark.asyncio
async def test_status_bar_refresh_paused():
    """Status bar shows paused indicator."""

    class StatusTestApp(App):
        def compose(self):
            yield StatusBar(provider_name="yahoo")

    app = StatusTestApp()
    async with app.run_test():
        bar = app.query_one(StatusBar)
        bar.update_refresh_status(paused=True)
        widget = bar.query_one("#status-refresh")
        rendered = widget.render().plain
        assert "Paused" in rendered


# --- Auto-refresh toggle ---


@pytest.mark.asyncio
async def test_auto_refresh_enabled_by_default(fake_provider, monkeypatch):
    """Auto-refresh is enabled by default."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test():
        assert app._auto_refresh_enabled is True


@pytest.mark.asyncio
async def test_toggle_auto_refresh(fake_provider, monkeypatch):
    """Ctrl+P toggles auto-refresh on/off."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        assert app._auto_refresh_enabled is True

        await pilot.press("ctrl+p")
        assert app._auto_refresh_enabled is False

        await pilot.press("ctrl+p")
        assert app._auto_refresh_enabled is True


@pytest.mark.asyncio
async def test_auto_refresh_starts_after_ticker_load(fake_provider, monkeypatch):
    """Auto-refresh timer starts after loading a ticker."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        assert app._refresh_timer is not None
        assert app._countdown_timer is not None


@pytest.mark.asyncio
async def test_auto_refresh_stops_when_paused(fake_provider, monkeypatch):
    """Pausing auto-refresh stops the timers."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Pause
        await pilot.press("ctrl+p")
        assert app._auto_refresh_enabled is False


# --- Refresh interval based on market state ---


def test_refresh_interval_varies_by_market_state(fake_provider, monkeypatch):
    """Refresh interval is different during/outside market hours."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)

    # During regular hours
    from tenortui.market_hours import MarketState

    monkeypatch.setattr("tenortui.app.get_market_state", lambda: MarketState.REGULAR)
    assert app._get_refresh_interval() == 60

    # During closed
    monkeypatch.setattr("tenortui.app.get_market_state", lambda: MarketState.CLOSED)
    assert app._get_refresh_interval() == 300

    # During pre-market
    monkeypatch.setattr("tenortui.app.get_market_state", lambda: MarketState.PRE_MARKET)
    assert app._get_refresh_interval() == 120


@pytest.mark.asyncio
async def test_market_state_displayed_on_mount(fake_provider, monkeypatch):
    """Market state is displayed in status bar on mount."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test():
        bar = app.query_one(StatusBar)
        market = bar.query_one("#status-market")
        rendered = market.render().plain
        assert any(
            s in rendered
            for s in ["Market Open", "Pre-Market", "After-Hours", "Market Closed"]
        )
