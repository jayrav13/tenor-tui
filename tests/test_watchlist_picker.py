# tests/test_watchlist_picker.py
from tenortui.watchlists import WatchlistData, Watchlist
from tenortui.widgets.watchlist_picker import WatchlistPicker, WatchlistManager


class TestWatchlistPickerInit:
    def test_stores_watchlist_names(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="Default"), Watchlist(name="Tech")]
        )
        picker = WatchlistPicker(data)
        assert picker._watchlist_data is data
        assert len(data.watchlists) == 2


class TestWatchlistManagerInit:
    def test_stores_data(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        manager = WatchlistManager(data)
        assert manager._watchlist_data is data
