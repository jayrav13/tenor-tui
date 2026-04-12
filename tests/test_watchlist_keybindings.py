# tests/test_watchlist_keybindings.py
"""Tests for w/W/d keybindings for watchlist management."""

import pytest

from tenortui.app import TenorTUI
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_panel import WatchlistPanel
from tenortui.widgets.watchlist_picker import WatchlistPicker, WatchlistManager


def _make_app(fake_provider, monkeypatch, watchlist_data=None):
    if watchlist_data is None:
        watchlist_data = WatchlistData(watchlists=[Watchlist(name="Default")])
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: watchlist_data,
    )
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
    return TenorTUI(provider=fake_provider)


# ---------------------------------------------------------------------------
# w key — add to watchlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_w_key_no_symbol_does_nothing(fake_provider, monkeypatch):
    """Pressing w with no loaded ticker should not open WatchlistPicker."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        app.set_focus(None)
        await pilot.press("w")
        # screen_stack stays at 1 — no modal pushed
        assert len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_w_key_with_symbol_opens_picker(fake_provider, monkeypatch):
    """Pressing w after loading a ticker should open WatchlistPicker."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        # Load a ticker first
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Unfocus input so on_key fires
        app.set_focus(None)
        await pilot.press("w")
        await pilot.pause()
        # Modal pushed onto stack
        assert len(app.screen_stack) == 2
        assert isinstance(app.screen, WatchlistPicker)


@pytest.mark.asyncio
async def test_w_key_equity_item_stored_as_pending(fake_provider, monkeypatch):
    """After pressing w, _pending_watchlist_item is an equity WatchlistItem."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        app.set_focus(None)
        await pilot.press("w")
        await pilot.pause()
        assert hasattr(app, "_pending_watchlist_item")
        item = app._pending_watchlist_item
        assert item.type == "equity"
        assert item.symbol == "AAPL"


@pytest.mark.asyncio
async def test_on_watchlist_picked_adds_item(fake_provider, monkeypatch):
    """_on_watchlist_picked with a valid index adds item to watchlist data."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test():
        app._current_symbol = "MSFT"
        item = WatchlistItem(type="equity", symbol="MSFT")
        app._pending_watchlist_item = item

        initial_count = len(app._watchlist_data.watchlists[0].items)
        app._on_watchlist_picked(0)

        assert len(app._watchlist_data.watchlists[0].items) == initial_count + 1
        assert any(i.symbol == "MSFT" for i in app._watchlist_data.watchlists[0].items)


@pytest.mark.asyncio
async def test_on_watchlist_picked_none_does_nothing(fake_provider, monkeypatch):
    """_on_watchlist_picked with None result should not add anything."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test():
        app._current_symbol = "GOOG"
        item = WatchlistItem(type="equity", symbol="GOOG")
        app._pending_watchlist_item = item

        initial_count = len(app._watchlist_data.watchlists[0].items)
        app._on_watchlist_picked(None)

        assert len(app._watchlist_data.watchlists[0].items) == initial_count


@pytest.mark.asyncio
async def test_on_watchlist_picked_no_pending_item_does_nothing(
    fake_provider, monkeypatch
):
    """_on_watchlist_picked without _pending_watchlist_item should not crash."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test():
        # Ensure no _pending_watchlist_item exists
        if hasattr(app, "_pending_watchlist_item"):
            del app._pending_watchlist_item
        initial_count = len(app._watchlist_data.watchlists[0].items)
        app._on_watchlist_picked(0)  # should not raise
        assert len(app._watchlist_data.watchlists[0].items) == initial_count


# ---------------------------------------------------------------------------
# W key — open watchlist manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_W_key_opens_manager(fake_provider, monkeypatch):
    """Pressing W opens WatchlistManager modal."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        app.set_focus(None)
        await pilot.press("W")
        await pilot.pause()
        assert len(app.screen_stack) == 2
        assert isinstance(app.screen, WatchlistManager)


@pytest.mark.asyncio
async def test_on_watchlist_manager_closed_none_does_nothing(
    fake_provider, monkeypatch
):
    """_on_watchlist_manager_closed with None does not modify watchlist_data."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test():
        original_data = app._watchlist_data
        app._on_watchlist_manager_closed(None)
        assert app._watchlist_data is original_data


@pytest.mark.asyncio
async def test_on_watchlist_manager_closed_with_data_updates(
    fake_provider, monkeypatch
):
    """_on_watchlist_manager_closed with new data updates _watchlist_data."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test():
        new_data = WatchlistData(
            watchlists=[Watchlist(name="Updated"), Watchlist(name="NewList")]
        )
        # _fetch_watchlist_quotes tries to access active_index watchlist items;
        # patch it out to keep this test focused on data update behavior.
        monkeypatch.setattr(app, "_fetch_watchlist_quotes", lambda: None)
        app._on_watchlist_manager_closed(new_data)
        assert app._watchlist_data is new_data
        assert len(app._watchlist_data.watchlists) == 2


# ---------------------------------------------------------------------------
# d key — remove from watchlist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_d_key_no_listview_focused_does_nothing(fake_provider, monkeypatch):
    """Pressing d when a ListView is not focused should not remove items."""
    watchlist_data = WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[WatchlistItem(type="equity", symbol="AAPL")],
            )
        ]
    )
    app = _make_app(fake_provider, monkeypatch, watchlist_data)
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    async with app.run_test() as pilot:
        # Force focus on something that is NOT a ListView
        app.set_focus(None)
        await pilot.press("d")
        await pilot.pause()
        # Item should still be there
        assert len(app._watchlist_data.watchlists[0].items) == 1


@pytest.mark.asyncio
async def test_action_remove_from_watchlist_removes_item(fake_provider, monkeypatch):
    """_action_remove_from_watchlist with WatchlistPanel ListView focused removes item."""
    from textual.widgets import ListView

    watchlist_data = WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[
                    WatchlistItem(type="equity", symbol="AAPL"),
                    WatchlistItem(type="equity", symbol="MSFT"),
                ],
            )
        ]
    )
    app = _make_app(fake_provider, monkeypatch, watchlist_data)
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()

        # Focus the ListView inside WatchlistPanel
        panel = app.query_one(WatchlistPanel)
        lv = panel.query_one(ListView)
        lv.focus()
        lv.index = 0
        await pilot.pause()

        initial_count = len(app._watchlist_data.watchlists[0].items)
        # Call directly — remove_item mutates data in-place; set_watchlists may raise
        # DuplicateIds in tests (pre-existing issue) but is wrapped in try/except.
        app._action_remove_from_watchlist()

        assert len(app._watchlist_data.watchlists[0].items) == initial_count - 1


# ---------------------------------------------------------------------------
# _get_contract_from_chain_table
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_contract_from_chain_table_with_symbol_returns_item(
    fake_provider, monkeypatch
):
    """_get_contract_from_chain_table returns a WatchlistItem for a valid row."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        from textual.widgets import DataTable

        from tenortui.widgets.chain_table import ChainTable

        tables = list(app.query_one(ChainTable).query(DataTable))
        table = tables[0]
        table.focus()
        # Move cursor to row 0 (first strike row, before ATM divider)
        table.move_cursor(row=0)
        await pilot.pause()

        # With symbol+expiration set, it should return a WatchlistItem
        assert app._current_symbol is not None
        assert app._current_expiration is not None
        result = app._get_contract_from_chain_table()
        # Should return an option WatchlistItem (first row, strike 200.0)
        assert result is not None
        assert result.type == "option"
        assert result.strike == 200.0
        assert result.option_type == "call"


@pytest.mark.asyncio
async def test_get_contract_returns_none_without_symbol(fake_provider, monkeypatch):
    """_get_contract_from_chain_table returns None when _current_symbol is None."""
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        from textual.widgets import DataTable

        from tenortui.widgets.chain_table import ChainTable

        tables = list(app.query_one(ChainTable).query(DataTable))
        table = tables[0]
        table.focus()
        table.move_cursor(row=0)
        await pilot.pause()

        # Clear symbol so it returns None
        app._current_symbol = None
        result = app._get_contract_from_chain_table()
        assert result is None
