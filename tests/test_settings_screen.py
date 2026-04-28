import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

from tenortui.app import TenorTUI
from tenortui.watchlists import WatchlistData, Watchlist
from tenortui.config import AppConfig
from tenortui.widgets.settings_screen import SettingsScreen


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Prevent tests from reading/writing the real config file."""
    monkeypatch.setattr(
        "tenortui.widgets.settings_screen.resolve_config_path",
        lambda: tmp_path / "config.yaml",
    )
    monkeypatch.setattr(
        "tenortui.config.resolve_config_path",
        lambda: tmp_path / "config.yaml",
    )


class SettingsApp(App):
    BINDINGS = [("comma", "settings", "Settings")]

    def compose(self) -> ComposeResult:
        yield from ()

    def action_settings(self) -> None:
        config = AppConfig(provider_name="yahoo")
        self.push_screen(SettingsScreen(config))


@pytest.mark.asyncio
async def test_settings_screen_renders():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, SettingsScreen)
        title = screen.query_one("#settings-title")
        assert "Settings" in title.render().plain


@pytest.mark.asyncio
async def test_j_moves_cursor_down():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        assert screen._cursor_index == 0
        await pilot.press("j")
        await pilot.pause()
        assert screen._cursor_index == 1
        assert screen._rows[1].has_class("focused")
        assert not screen._rows[0].has_class("focused")


@pytest.mark.asyncio
async def test_k_moves_cursor_up():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        await pilot.press("j")
        await pilot.press("j")
        await pilot.pause()
        assert screen._cursor_index == 2
        await pilot.press("k")
        await pilot.pause()
        assert screen._cursor_index == 1


@pytest.mark.asyncio
async def test_cursor_stays_at_bounds():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        await pilot.press("k")  # Already at top
        await pilot.pause()
        assert screen._cursor_index == 0


@pytest.mark.asyncio
async def test_enter_toggles_boolean():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        greeks_row = None
        for i, row in enumerate(screen._rows):
            if row.key == "yahoo.greeks.enabled":
                greeks_row = row
                for _ in range(i):
                    await pilot.press("j")
                break
        assert greeks_row is not None
        original = greeks_row.current_value
        await pilot.press("enter")
        await pilot.pause()
        assert greeks_row.current_value != original
        assert greeks_row.is_modified


@pytest.mark.asyncio
async def test_enter_cycles_provider():
    from tenortui.config import KNOWN_PROVIDERS

    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        assert screen._rows[0].key == "default"
        assert screen._rows[0].current_value == "yahoo"
        ordered = sorted(KNOWN_PROVIDERS)
        next_provider = ordered[(ordered.index("yahoo") + 1) % len(ordered)]
        await pilot.press("enter")
        await pilot.pause()
        assert screen._rows[0].current_value == next_provider


@pytest.mark.asyncio
async def test_q_bang_discards_and_closes():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("enter")  # Toggle first setting
        await pilot.pause()
        # :q!
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press(*"q!")
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, SettingsScreen)


@pytest.mark.asyncio
async def test_q_warns_on_unsaved_changes():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        await pilot.press("enter")  # Make a change
        await pilot.pause()
        # :q (should warn, not close)
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press("q")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        status = screen.query_one("#settings-status", Static)
        assert "Unsaved" in status.render().plain


@pytest.mark.asyncio
async def test_q_closes_when_no_changes():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press("q")
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, SettingsScreen)


@pytest.mark.asyncio
async def test_inline_number_editing():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        target_row = None
        for i, row in enumerate(screen._rows):
            if row.key == "spread_thresholds.tight":
                target_row = row
                for _ in range(i):
                    await pilot.press("j")
                break
        assert target_row is not None
        await pilot.press("enter")  # Start editing
        await pilot.pause()
        edit_input = screen.query_one("#edit-spread_thresholds-tight", Input)
        edit_input.value = "3.0"
        await pilot.press("enter")  # Confirm
        await pilot.pause()
        assert target_row.current_value == "3.0"
        assert target_row.is_modified


@pytest.mark.asyncio
async def test_invalid_number_rejected():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        target_row = None
        for i, row in enumerate(screen._rows):
            if row.key == "refresh.regular":
                target_row = row
                for _ in range(i):
                    await pilot.press("j")
                break
        assert target_row is not None
        original = target_row.current_value
        await pilot.press("enter")
        await pilot.pause()
        edit_input = screen.query_one("#edit-refresh-regular", Input)
        edit_input.value = "not_a_number"
        await pilot.press("enter")
        await pilot.pause()
        assert target_row.current_value == original
        status = screen.query_one("#settings-status", Static)
        assert "Invalid" in status.render().plain


@pytest.mark.asyncio
async def test_w_saves_without_closing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tenortui.widgets.settings_screen.save_config",
        lambda changes, **kw: None,
    )
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        await pilot.press("enter")  # Toggle provider
        await pilot.pause()
        assert screen._has_unsaved_changes
        # :w
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press("w")
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        assert not screen._has_unsaved_changes
        status = screen.query_one("#settings-status", Static)
        assert "saved" in status.render().plain.lower()


@pytest.mark.asyncio
async def test_comma_closes_settings():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        await pilot.press("comma")  # Close via comma
        await pilot.pause()
        assert not isinstance(app.screen, SettingsScreen)


@pytest.mark.asyncio
async def test_modified_title_indicator():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        title = screen.query_one("#settings-title", Static)
        assert "[modified]" not in title.render().plain
        await pilot.press("enter")  # Toggle provider
        await pilot.pause()
        assert "[modified]" in title.render().plain


# --- Integration tests with TenorTUI ---


@pytest.fixture
def tenor_app(fake_provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
    )
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_comma_opens_settings_from_app(tenor_app):
    async with tenor_app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(tenor_app.screen, SettingsScreen)


@pytest.mark.asyncio
async def test_wq_saves_and_hot_applies(tenor_app, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tenortui.widgets.settings_screen.save_config",
        lambda changes, **kw: None,
    )
    async with tenor_app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = tenor_app.screen
        # Navigate to yahoo.greeks.enabled and toggle it
        for i, row in enumerate(screen._rows):
            if row.key == "yahoo.greeks.enabled":
                for _ in range(i):
                    await pilot.press("j")
                break
        await pilot.press("enter")  # Toggle greeks
        await pilot.pause()
        # :wq
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press(*"wq")
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(tenor_app.screen, SettingsScreen)
        assert tenor_app._greeks_config.enabled is True
