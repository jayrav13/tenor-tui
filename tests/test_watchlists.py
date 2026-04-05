import json

from tenortui.watchlists import (
    WatchlistItem,
    Watchlist,
    WatchlistData,
    load_watchlists,
    save_watchlists,
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
