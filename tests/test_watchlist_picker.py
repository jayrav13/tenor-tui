# tests/test_watchlist_picker.py
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Label, ListView

from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_picker import WatchlistPicker, WatchlistManager


# --- Init tests (existing) ---


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


# --- Helpers ---


def _make_data(*names: str) -> WatchlistData:
    return WatchlistData(
        watchlists=[Watchlist(name=n) for n in names],
        active_index=0,
    )


def _make_data_with_items() -> WatchlistData:
    return WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[WatchlistItem(type="equity", symbol="AAPL")],
            ),
            Watchlist(
                name="Tech",
                items=[
                    WatchlistItem(type="equity", symbol="GOOG"),
                    WatchlistItem(type="equity", symbol="MSFT"),
                ],
            ),
        ],
        active_index=0,
    )


class PickerApp(App):
    """Test app that pushes WatchlistPicker as a modal."""

    def __init__(self, data: WatchlistData):
        super().__init__()
        self._data = data
        self.dismiss_result = "NOT_SET"

    def compose(self) -> ComposeResult:
        yield from ()

    def on_mount(self) -> None:
        self.push_screen(WatchlistPicker(self._data), callback=self._on_dismiss)

    def _on_dismiss(self, result) -> None:
        self.dismiss_result = result


class ManagerApp(App):
    """Test app that pushes WatchlistManager as a modal."""

    def __init__(self, data: WatchlistData):
        super().__init__()
        self._data = data
        self.dismiss_result = "NOT_SET"

    def compose(self) -> ComposeResult:
        yield from ()

    def on_mount(self) -> None:
        self.push_screen(WatchlistManager(self._data), callback=self._on_dismiss)

    def _on_dismiss(self, result) -> None:
        self.dismiss_result = result


# --- WatchlistPicker async tests ---


@pytest.mark.asyncio
async def test_picker_shows_watchlist_names():
    """WatchlistPicker displays watchlist names in the list."""
    data = _make_data("Default", "Tech", "Finance")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistPicker)
        lv = screen.query_one(ListView)
        items = list(lv.query("ListItem"))
        assert len(items) == 3


@pytest.mark.asyncio
async def test_picker_select_returns_index():
    """Selecting a watchlist dismisses picker with the selected index."""
    data = _make_data("Default", "Tech")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistPicker)
        # Select the first item (index 0) via Enter
        lv = screen.query_one(ListView)
        lv.index = 0
        await pilot.press("enter")
        await pilot.pause()
        assert app.dismiss_result == 0


@pytest.mark.asyncio
async def test_picker_cancel_returns_none():
    """Pressing escape dismisses picker with None."""
    data = _make_data("Default")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistPicker)
        await pilot.press("escape")
        await pilot.pause()
        assert app.dismiss_result is None


@pytest.mark.asyncio
async def test_picker_new_watchlist_flow():
    """Pressing n shows input, submitting creates watchlist and returns new index."""
    data = _make_data("Default")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistPicker)

        # Show the new watchlist input
        await pilot.press("n")
        await pilot.pause()
        inp = screen.query_one("#picker-new-input", Input)
        assert inp.display is True

        # Type and submit a name
        inp.value = "My New List"
        inp.focus()
        await pilot.press("enter")
        await pilot.pause()
        # Should dismiss with index of the newly created watchlist
        assert app.dismiss_result == 1
        assert data.watchlists[-1].name == "My New List"


@pytest.mark.asyncio
async def test_picker_new_watchlist_cancel():
    """Pressing escape while creating cancels the new watchlist input."""
    data = _make_data("Default")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistPicker)

        await pilot.press("n")
        await pilot.pause()
        inp = screen.query_one("#picker-new-input", Input)
        assert inp.display is True

        # Pressing escape hides input, doesn't dismiss modal
        await pilot.press("escape")
        await pilot.pause()
        assert inp.display is False
        assert isinstance(app.screen, WatchlistPicker)


@pytest.mark.asyncio
async def test_picker_n_ignored_while_creating():
    """Pressing n while already creating is ignored."""
    data = _make_data("Default")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        await pilot.press("n")
        await pilot.pause()
        assert screen._creating_new is True
        # Pressing n again should be a no-op
        await pilot.press("n")
        await pilot.pause()
        assert screen._creating_new is True


@pytest.mark.asyncio
async def test_picker_cursor_nav():
    """j/k navigate the list, suppressed during create mode."""
    data = _make_data("Default", "Tech", "Finance")
    app = PickerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.focus()
        lv.index = 0
        await pilot.pause()

        # Call actions directly to avoid key binding conflicts
        screen.action_cursor_down()
        await pilot.pause()
        assert lv.index == 1

        screen.action_cursor_up()
        await pilot.pause()
        assert lv.index == 0

        # In create mode, j/k should be suppressed
        screen._creating_new = True
        screen.action_cursor_down()
        await pilot.pause()
        assert lv.index == 0  # unchanged


# --- WatchlistManager async tests ---


@pytest.mark.asyncio
async def test_manager_shows_watchlist_names_with_counts():
    """WatchlistManager shows watchlist names with item counts."""
    data = _make_data_with_items()
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistManager)
        lv = screen.query_one(ListView)
        items = list(lv.query("ListItem"))
        assert len(items) == 2
        labels = [item.query_one(Label).render().plain for item in items]
        assert "Default (1 item)" in labels[0]
        assert "Tech (2 items)" in labels[1]


@pytest.mark.asyncio
async def test_manager_delete_removes_watchlist():
    """Pressing d deletes the selected watchlist."""
    data = _make_data_with_items()
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.index = 1  # select "Tech"
        await pilot.pause()

        await pilot.press("d")
        await pilot.pause()
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"
        # List should be rebuilt
        items = list(lv.query("ListItem"))
        assert len(items) == 1


@pytest.mark.asyncio
async def test_manager_delete_prevented_when_single():
    """Cannot delete the last remaining watchlist."""
    data = _make_data("Only One")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.index = 0
        await pilot.pause()

        await pilot.press("d")
        await pilot.pause()
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Only One"


@pytest.mark.asyncio
async def test_manager_rename_flow():
    """Pressing r shows input with current name, submitting renames."""
    data = _make_data_with_items()
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.index = 0
        await pilot.pause()

        await pilot.press("r")
        await pilot.pause()
        inp = screen.query_one("#manager-input", Input)
        assert inp.display is True
        assert inp.value == "Default"

        inp.value = "Favorites"
        inp.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert data.watchlists[0].name == "Favorites"
        assert inp.display is False


@pytest.mark.asyncio
async def test_manager_new_watchlist_flow():
    """Pressing n shows input, submitting creates a new watchlist."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen

        await pilot.press("n")
        await pilot.pause()
        inp = screen.query_one("#manager-input", Input)
        assert inp.display is True

        inp.value = "New WL"
        inp.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert len(data.watchlists) == 2
        assert data.watchlists[-1].name == "New WL"
        assert inp.display is False


@pytest.mark.asyncio
async def test_manager_close_returns_data():
    """Pressing escape dismisses manager with the data."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, WatchlistManager)

        await pilot.press("escape")
        await pilot.pause()
        assert app.dismiss_result is data


@pytest.mark.asyncio
async def test_manager_escape_while_editing_cancels_edit():
    """Pressing escape while editing cancels the input instead of closing."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen

        await pilot.press("n")
        await pilot.pause()
        inp = screen.query_one("#manager-input", Input)
        assert inp.display is True

        await pilot.press("escape")
        await pilot.pause()
        assert inp.display is False
        assert isinstance(app.screen, WatchlistManager)


@pytest.mark.asyncio
async def test_manager_n_ignored_while_editing():
    """Pressing n while already editing is ignored."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        await pilot.press("n")
        await pilot.pause()
        assert screen._editing == "new"
        await pilot.press("n")
        await pilot.pause()
        assert screen._editing == "new"


@pytest.mark.asyncio
async def test_manager_r_ignored_while_editing():
    """Pressing r while already editing is ignored."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        await pilot.press("n")
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert screen._editing == "new"


@pytest.mark.asyncio
async def test_manager_d_ignored_while_editing():
    """Pressing d while already editing is ignored."""
    data = _make_data("Default", "Tech")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert len(data.watchlists) == 2


@pytest.mark.asyncio
async def test_manager_cursor_nav():
    """j/k navigate the manager list, suppressed during editing."""
    data = _make_data("Default", "Tech", "Finance")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.focus()
        lv.index = 0
        await pilot.pause()

        # Call actions directly to avoid key binding conflicts
        screen.action_cursor_down()
        await pilot.pause()
        assert lv.index == 1

        screen.action_cursor_up()
        await pilot.pause()
        assert lv.index == 0

        # In editing mode, j/k suppressed
        screen._editing = "rename"
        screen.action_cursor_down()
        await pilot.pause()
        assert lv.index == 0


@pytest.mark.asyncio
async def test_manager_rename_no_selection():
    """Pressing r with no selection does nothing."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.index = None
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        assert screen._editing is None


@pytest.mark.asyncio
async def test_manager_delete_no_selection():
    """Pressing d with no selection does nothing."""
    data = _make_data("Default", "Tech")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        lv = screen.query_one(ListView)
        lv.index = None
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        assert len(data.watchlists) == 2


@pytest.mark.asyncio
async def test_manager_empty_input_ignored():
    """Submitting empty input during new/rename is ignored."""
    data = _make_data("Default")
    app = ManagerApp(data)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        await pilot.press("n")
        await pilot.pause()
        inp = screen.query_one("#manager-input", Input)
        inp.value = "   "
        inp.focus()
        await pilot.press("enter")
        await pilot.pause()
        # Should not create a new watchlist with blank name
        assert len(data.watchlists) == 1
