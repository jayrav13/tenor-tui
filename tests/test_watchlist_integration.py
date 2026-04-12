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
    async def test_ticker_added_to_watchlist_on_search(
        self, fake_provider, monkeypatch
    ):
        wl_data = WatchlistData(watchlists=[Watchlist(name="Default")], active_index=0)
        monkeypatch.setattr("tenortui.app.migrate_from_history", lambda: wl_data)
        monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
        monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: [])
        monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda q: q)
        app = TenorTUI(provider=fake_provider)
        async with app.run_test() as pilot:
            app.action_focus_search()
            await pilot.press(*"AAPL")
            await pilot.press("enter")
            await app.workers.wait_for_complete()

            assert any(
                item.symbol == "AAPL" and item.type == "equity"
                for item in wl_data.watchlists[0].items
            )
