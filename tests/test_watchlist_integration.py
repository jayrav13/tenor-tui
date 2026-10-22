# tests/test_watchlist_integration.py
import json

import pytest

from tenortui.app import TenorTUI
from tenortui.watchlists import (
    WatchlistData,
    Watchlist,
    WatchlistItem,
    load_watchlists,
    save_watchlists,
    migrate_from_history,
)
from tenortui.widgets.watchlist_panel import WatchlistPanel
from tenortui.widgets.watchlist_picker import WatchlistPicker


class TestMigrationIntegration:
    def test_migrates_history_on_first_run(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL", "MSFT"]))

        data = migrate_from_history(history_path, watchlists_path)

        assert watchlists_path.exists()
        assert len(data.watchlists) == 1
        assert len(data.watchlists[0].items) == 2
        assert data.watchlists[0].items[0].symbol == "AAPL"
        assert data.watchlists[0].items[1].symbol == "MSFT"

    def test_does_not_overwrite_existing_watchlists(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL"]))
        existing = WatchlistData(
            watchlists=[
                Watchlist(
                    name="My List",
                    items=[WatchlistItem(type="equity", symbol="GOOG")],
                )
            ]
        )
        save_watchlists(existing, watchlists_path)

        data = migrate_from_history(history_path, watchlists_path)
        assert data.watchlists[0].name == "My List"
        assert data.watchlists[0].items[0].symbol == "GOOG"


class TestWatchlistPersistence:
    def test_save_and_load_round_trip(self, tmp_path):
        path = tmp_path / "watchlists.json"
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Tech",
                    items=[
                        WatchlistItem(type="equity", symbol="AAPL"),
                        WatchlistItem(
                            type="option",
                            symbol="AAPL",
                            strike=180.0,
                            option_type="put",
                            expiration="2026-04-17",
                        ),
                    ],
                ),
                Watchlist(name="Finance", items=[]),
            ],
            active_index=1,
        )
        save_watchlists(data, path)
        loaded = load_watchlists(path)

        assert len(loaded.watchlists) == 2
        assert loaded.watchlists[0].name == "Tech"
        assert loaded.active_index == 1
        assert loaded.watchlists[0].items[1].strike == 180.0
        assert loaded.watchlists[0].items[1].option_type == "put"


class TestAppWithWatchlists:
    @pytest.mark.asyncio
    async def test_watchlist_panel_mounted(self, fake_provider, monkeypatch):
        monkeypatch.setattr(
            "tenortui.app.migrate_from_history",
            lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
        )
        app = TenorTUI(provider=fake_provider)
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_search_leaves_watchlists_unchanged(self, fake_provider, monkeypatch):
        """Browsing a ticker must not add it to any list (#67)."""
        wl_data = WatchlistData(
            watchlists=[
                Watchlist(name="Default"),
                Watchlist(
                    name="Core", items=[WatchlistItem(type="equity", symbol="MSFT")]
                ),
            ],
            active_index=0,
        )
        saves = []
        monkeypatch.setattr("tenortui.app.migrate_from_history", lambda: wl_data)
        monkeypatch.setattr(
            "tenortui.app.save_watchlists", lambda data, **kw: saves.append(data)
        )
        monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: [])
        monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda q: q)
        app = TenorTUI(provider=fake_provider)
        async with app.run_test() as pilot:
            app.action_focus_search()
            await pilot.press(*"AAPL")
            await pilot.press("enter")
            await app.workers.wait_for_complete()

            assert wl_data.watchlists[0].items == []
            assert [i.symbol for i in wl_data.watchlists[1].items] == ["MSFT"]
            assert saves == []

    @pytest.mark.asyncio
    async def test_browsing_many_tickers_keeps_curated_list(
        self, fake_provider, monkeypatch
    ):
        """Repro from #67: browsing 15 tickers leaves ["AAPL"] as ["AAPL"]."""
        wl_data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Core", items=[WatchlistItem(type="equity", symbol="AAPL")]
                )
            ],
            active_index=0,
        )
        monkeypatch.setattr("tenortui.app.migrate_from_history", lambda: wl_data)
        monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
        monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: [])
        monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda q: q)
        app = TenorTUI(provider=fake_provider)
        async with app.run_test():
            for i in range(15):
                app._load_ticker(f"T{i:02d}")
                await app.workers.wait_for_complete()

        assert [it.symbol for it in wl_data.watchlists[0].items] == ["AAPL"]

    @pytest.mark.asyncio
    async def test_w_key_still_adds_browsed_ticker(self, fake_provider, monkeypatch):
        """After browsing, pressing w and picking a list adds the ticker."""
        wl_data = WatchlistData(watchlists=[Watchlist(name="Default")], active_index=0)
        saves = []
        monkeypatch.setattr("tenortui.app.migrate_from_history", lambda: wl_data)
        monkeypatch.setattr(
            "tenortui.app.save_watchlists", lambda data, **kw: saves.append(data)
        )
        monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: [])
        monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda q: q)
        app = TenorTUI(provider=fake_provider)
        async with app.run_test() as pilot:
            app.action_focus_search()
            await pilot.press(*"AAPL")
            await pilot.press("enter")
            await app.workers.wait_for_complete()

            app.set_focus(None)
            await pilot.press("w")
            await pilot.pause()
            assert isinstance(app.screen, WatchlistPicker)
            # Pick the first list, as Enter on the highlighted row does.
            app.screen.dismiss(0)
            await pilot.pause()

            assert [(i.type, i.symbol) for i in wl_data.watchlists[0].items] == [
                ("equity", "AAPL")
            ]
            assert len(saves) == 1
