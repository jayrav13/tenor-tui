"""Tests for returning to the watchlist panel after a ticker load (#66)."""

import pytest
from textual.widgets import DataTable, ListView

from tenortui.app import TenorTUI
from tenortui.watchlists import Watchlist, WatchlistData, WatchlistItem
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.command_palette import CommandPalette
from tenortui.widgets.help_overlay import KEYBINDINGS
from tenortui.widgets.watchlist_panel import WatchlistPanel


def _make_app(fake_provider, monkeypatch, symbols=("MSFT",)):
    data = WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[WatchlistItem(type="equity", symbol=s) for s in symbols],
            )
        ]
    )
    monkeypatch.setattr("tenortui.app.migrate_from_history", lambda: data)
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda d, **kw: None)
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda q: q)
    return TenorTUI(provider=fake_provider)


async def _load_and_focus_chain(app, pilot):
    app._current_symbol = "AAPL"
    app._load_ticker("AAPL")
    await app.workers.wait_for_complete()
    await pilot.pause()
    table = app.query_one(ChainTable).query(DataTable).first()
    table.focus()
    await pilot.pause()
    return table


def _symbols(app):
    return [i.symbol for i in app._watchlist_data.watchlists[0].items]


@pytest.mark.asyncio
async def test_b_key_shows_watchlist_after_ticker_load(fake_provider, monkeypatch):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        panel = app.query_one(WatchlistPanel)
        await _load_and_focus_chain(app, pilot)
        assert panel.display is False

        await pilot.press("b")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert panel.display is True
        assert app.query_one(ChainTable).display is False
        assert app.focused is panel.query_one(ListView)


@pytest.mark.asyncio
async def test_show_watchlist_refreshes_quotes(fake_provider, monkeypatch):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await _load_and_focus_chain(app, pilot)
        calls = []
        monkeypatch.setattr(
            "tenortui.app.batch_quotes", lambda syms: calls.append(syms) or []
        )
        app.action_show_watchlist()
        await app.workers.wait_for_complete()
        assert calls, "showing the panel should fetch fresh quotes"


@pytest.mark.asyncio
async def test_watchlist_command_shows_panel(fake_provider, monkeypatch):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        panel = app.query_one(WatchlistPanel)
        for cmd in ("watchlist", "wl"):
            await _load_and_focus_chain(app, pilot)
            assert panel.display is False
            app.post_message(CommandPalette.CommandSubmitted(cmd))
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert panel.display is True, cmd


@pytest.mark.asyncio
async def test_show_watchlist_when_empty_at_launch(fake_provider, monkeypatch):
    """Panel hidden at launch (no items) can be shown after the first load."""
    app = _make_app(fake_provider, monkeypatch, symbols=())
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        panel = app.query_one(WatchlistPanel)
        assert panel.display is False
        await _load_and_focus_chain(app, pilot)
        app.action_show_watchlist()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert panel.display is True


@pytest.mark.asyncio
async def test_selecting_from_reshown_panel_shows_chain(fake_provider, monkeypatch):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await _load_and_focus_chain(app, pilot)
        app.action_show_watchlist()
        await app.workers.wait_for_complete()
        await pilot.pause()

        app.post_message(WatchlistPanel.TickerSelected("MSFT"))
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app.query_one(WatchlistPanel).display is False
        assert app.query_one(ChainTable).display is True
        assert app._current_symbol == "MSFT"


@pytest.mark.asyncio
async def test_watchlist_refresh_does_not_steal_focus_from_chain(
    fake_provider, monkeypatch
):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        table = await _load_and_focus_chain(app, pilot)
        app._fetch_watchlist_quotes()  # what _on_auto_refresh does every cycle
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.focused is table, f"focus stolen by {app.focused!r}"


@pytest.mark.asyncio
async def test_d_does_not_delete_from_hidden_panel(fake_provider, monkeypatch):
    app = _make_app(fake_provider, monkeypatch)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await _load_and_focus_chain(app, pilot)
        before = _symbols(app)
        # Simulate focus landing on the hidden ListView by any route.
        lv = app.query_one(WatchlistPanel).query_one(ListView)
        app.set_focus(lv, scroll_visible=False)
        lv.index = 0
        app._action_remove_from_watchlist()  # what pressing "d" calls
        assert _symbols(app) == before


def test_help_overlay_lists_b_key():
    keys = [k for _, rows in KEYBINDINGS for k, _ in rows]
    assert "b" in keys
