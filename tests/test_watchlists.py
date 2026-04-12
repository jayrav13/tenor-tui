import json

from tenortui.watchlists import (
    WatchlistItem,
    Watchlist,
    WatchlistData,
    load_watchlists,
    save_watchlists,
    add_item,
    remove_item,
    create_watchlist,
    rename_watchlist,
    delete_watchlist,
    migrate_from_history,
)


class TestWatchlistItem:
    def test_equity_item(self):
        item = WatchlistItem(type="equity", symbol="AAPL")
        assert item.type == "equity"
        assert item.symbol == "AAPL"
        assert item.strike is None
        assert item.option_type is None
        assert item.expiration is None

    def test_option_item(self):
        item = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        assert item.type == "option"
        assert item.strike == 180.0
        assert item.option_type == "put"
        assert item.expiration == "2026-04-17"


class TestLoadWatchlists:
    def test_no_file_returns_default(self, tmp_path):
        data = load_watchlists(tmp_path / "watchlists.json")
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"
        assert data.watchlists[0].items == []
        assert data.active_index == 0

    def test_valid_file(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(
            json.dumps(
                {
                    "watchlists": [
                        {
                            "name": "Tech",
                            "items": [{"type": "equity", "symbol": "AAPL"}],
                        }
                    ],
                    "active_index": 0,
                }
            )
        )
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Tech"
        assert len(data.watchlists[0].items) == 1
        assert data.watchlists[0].items[0].symbol == "AAPL"

    def test_corrupt_file_returns_default(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text("not json")
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"

    def test_non_dict_returns_default(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(json.dumps(["not", "a", "dict"]))
        data = load_watchlists(path)
        assert len(data.watchlists) == 1

    def test_empty_watchlists_array_returns_default(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(json.dumps({"watchlists": [], "active_index": 0}))
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"

    def test_skips_malformed_items(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(
            json.dumps(
                {
                    "watchlists": [
                        {
                            "name": "Tech",
                            "items": [
                                # valid item
                                {"type": "equity", "symbol": "AAPL"},
                                # missing required field "symbol"
                                {"type": "equity"},
                                # unknown key — should be filtered, item kept
                                {
                                    "type": "equity",
                                    "symbol": "MSFT",
                                    "unknown_key": "x",
                                },
                                # not a dict
                                "bad_item",
                            ],
                        }
                    ],
                    "active_index": 0,
                }
            )
        )
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        items = data.watchlists[0].items
        # valid AAPL + filtered MSFT survive; missing-symbol and non-dict are skipped
        assert len(items) == 2
        symbols = [i.symbol for i in items]
        assert "AAPL" in symbols
        assert "MSFT" in symbols

    def test_active_index_out_of_range_clamped(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(
            json.dumps(
                {
                    "watchlists": [{"name": "Default", "items": []}],
                    "active_index": 99,
                }
            )
        )
        data = load_watchlists(path)
        assert data.active_index == 0

    def test_active_index_non_int_clamped(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(
            json.dumps(
                {
                    "watchlists": [{"name": "Default", "items": []}],
                    "active_index": "bad",
                }
            )
        )
        data = load_watchlists(path)
        assert data.active_index == 0


class TestSaveWatchlists:
    def test_round_trip(self, tmp_path):
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
                )
            ],
            active_index=0,
        )
        save_watchlists(data, path)
        loaded = load_watchlists(path)
        assert len(loaded.watchlists) == 1
        assert loaded.watchlists[0].name == "Tech"
        assert len(loaded.watchlists[0].items) == 2
        assert loaded.watchlists[0].items[1].strike == 180.0

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "watchlists.json"
        data = WatchlistData(
            watchlists=[Watchlist(name="Default", items=[])], active_index=0
        )
        save_watchlists(data, path)
        assert path.exists()

    def test_save_omits_none_fields_on_disk(self, tmp_path):
        path = tmp_path / "watchlists.json"
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Tech",
                    items=[WatchlistItem(type="equity", symbol="AAPL")],
                )
            ],
            active_index=0,
        )
        save_watchlists(data, path)
        raw = json.loads(path.read_text())
        item_dict = raw["watchlists"][0]["items"][0]
        assert "strike" not in item_dict
        assert "option_type" not in item_dict
        assert "expiration" not in item_dict

    def test_atomic_write_leaves_no_tmp_file(self, tmp_path):
        path = tmp_path / "watchlists.json"
        data = WatchlistData(
            watchlists=[Watchlist(name="Default", items=[])], active_index=0
        )
        save_watchlists(data, path)
        tmp_path_candidate = path.with_suffix(path.suffix + ".tmp")
        assert not tmp_path_candidate.exists()
        assert path.exists()


class TestAddItem:
    def test_add_equity(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        item = WatchlistItem(type="equity", symbol="AAPL")
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].symbol == "AAPL"

    def test_add_option(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        item = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].strike == 180.0

    def test_deduplicates_equity(self):
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default", items=[WatchlistItem(type="equity", symbol="AAPL")]
                )
            ]
        )
        item = WatchlistItem(type="equity", symbol="AAPL")
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1

    def test_deduplicates_option(self):
        existing = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        data = WatchlistData(watchlists=[Watchlist(name="Default", items=[existing])])
        result = add_item(data, 0, existing)
        assert len(result.watchlists[0].items) == 1

    def test_does_not_deduplicate_different_options(self):
        existing = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        new = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=200.0,
            option_type="call",
            expiration="2026-04-17",
        )
        data = WatchlistData(watchlists=[Watchlist(name="Default", items=[existing])])
        result = add_item(data, 0, new)
        assert len(result.watchlists[0].items) == 2


class TestRemoveItem:
    def test_removes_by_index(self):
        data = WatchlistData(
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
        result = remove_item(data, 0, 0)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].symbol == "MSFT"

    def test_invalid_index_returns_unchanged(self):
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default", items=[WatchlistItem(type="equity", symbol="AAPL")]
                )
            ]
        )
        result = remove_item(data, 0, 5)
        assert len(result.watchlists[0].items) == 1


class TestCreateWatchlist:
    def test_creates_new(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = create_watchlist(data, "Tech")
        assert len(result.watchlists) == 2
        assert result.watchlists[1].name == "Tech"
        assert result.watchlists[1].items == []


class TestRenameWatchlist:
    def test_renames(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = rename_watchlist(data, 0, "My List")
        assert result.watchlists[0].name == "My List"


class TestDeleteWatchlist:
    def test_deletes(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="Default"), Watchlist(name="Tech")]
        )
        result = delete_watchlist(data, 1)
        assert len(result.watchlists) == 1
        assert result.watchlists[0].name == "Default"

    def test_cannot_delete_last(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = delete_watchlist(data, 0)
        assert len(result.watchlists) == 1

    def test_adjusts_active_index(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="A"), Watchlist(name="B")], active_index=1
        )
        result = delete_watchlist(data, 1)
        assert result.active_index == 0


class TestMigrateFromHistory:
    def test_migrates_history(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL", "MSFT", "GOOG"]))
        data = migrate_from_history(history_path, watchlists_path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"
        assert len(data.watchlists[0].items) == 3
        assert data.watchlists[0].items[0].symbol == "AAPL"
        assert data.watchlists[0].items[0].type == "equity"
        assert data.watchlists[0].items[2].symbol == "GOOG"
        assert watchlists_path.exists()

    def test_no_history_returns_default(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        data = migrate_from_history(history_path, watchlists_path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].items == []

    def test_skips_if_watchlists_exist(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL"]))
        watchlists_path.write_text(
            json.dumps(
                {
                    "watchlists": [
                        {
                            "name": "Existing",
                            "items": [{"type": "equity", "symbol": "MSFT"}],
                        }
                    ],
                    "active_index": 0,
                }
            )
        )
        data = migrate_from_history(history_path, watchlists_path)
        assert data.watchlists[0].name == "Existing"
        assert len(data.watchlists[0].items) == 1
        assert data.watchlists[0].items[0].symbol == "MSFT"
