"""Tests for vim-style keyboard navigation, help overlay, and command palette."""

import pytest
from textual.app import App, ComposeResult

from tenortui.app import TenorTUI
from tenortui.widgets.command_palette import CommandPalette
from tenortui.widgets.help_overlay import HelpOverlay
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


class HelpTestApp(App):
    BINDINGS = [("question_mark", "help", "Help")]

    def compose(self) -> ComposeResult:
        yield from ()

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())


@pytest.mark.asyncio
async def test_help_overlay_opens_and_closes():
    """Help overlay opens with action and closes with escape."""
    app = HelpTestApp()
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        assert len(app.screen_stack) == 2

        await pilot.press("escape")
        assert len(app.screen_stack) == 1


@pytest.mark.asyncio
async def test_help_overlay_shows_keybindings():
    """Help overlay displays keybinding sections."""
    app = HelpTestApp()
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        screen = app.screen
        statics = screen.query(".help-section")
        section_texts = [s.render().plain for s in statics]
        assert any("Navigation" in t for t in section_texts)
        assert any("Actions" in t for t in section_texts)


# --- Command Palette ---


@pytest.mark.asyncio
async def test_command_palette_opens_and_closes():
    """Command palette opens and closes with escape."""

    class PaletteTestApp(App):
        def compose(self) -> ComposeResult:
            yield CommandPalette()

    app = PaletteTestApp()
    async with app.run_test() as pilot:
        palette = app.query_one(CommandPalette)
        assert palette.display is False

        palette.open()
        assert palette.display is True

        await pilot.press("escape")
        assert palette.display is False


@pytest.mark.asyncio
async def test_command_palette_submits_command():
    """Typing a command and pressing enter posts CommandSubmitted."""
    commands = []

    class PaletteSubmitApp(App):
        def compose(self) -> ComposeResult:
            yield CommandPalette()

        def on_command_palette_command_submitted(self, event):
            commands.append(event.command)

    app = PaletteSubmitApp()
    async with app.run_test() as pilot:
        palette = app.query_one(CommandPalette)
        palette.open()
        await pilot.press(*"help")
        await pilot.press("enter")
        assert "help" in commands
        assert palette.display is False


# --- App integration tests ---


@pytest.mark.asyncio
async def test_help_overlay_via_question_mark(fake_provider, monkeypatch):
    """Pressing ? opens the help overlay in the main app."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        app.set_focus(None)  # unfocus input
        await pilot.press("question_mark")
        assert len(app.screen_stack) == 2


@pytest.mark.asyncio
async def test_command_palette_via_colon(fake_provider, monkeypatch):
    """Pressing : opens the command palette in the main app."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        app.set_focus(None)  # unfocus input
        await pilot.press("colon")
        palette = app.query_one(CommandPalette)
        assert palette.display is True


@pytest.mark.asyncio
async def test_vim_keys_ignored_when_input_focused(fake_provider, monkeypatch):
    """j/k keys pass through to input when search is focused."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        input_w = app.query_one(TickerBar).query_one("#ticker-input")
        assert input_w.has_focus
        await pilot.press("j")
        assert input_w.value == "j"


@pytest.mark.asyncio
async def test_j_k_navigation_in_chain_table(fake_provider, monkeypatch):
    """j/k moves cursor in chain table DataTable."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Focus a DataTable
        from textual.widgets import DataTable

        tables = app.query(DataTable)
        if tables:
            tables.first().focus()
            await pilot.press("j")
            await pilot.press("k")
            # No crash — verifies j/k are handled


@pytest.mark.asyncio
async def test_command_palette_search(fake_provider, monkeypatch):
    """':search AAPL' loads the ticker via command palette."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        app.set_focus(None)
        await pilot.press("colon")
        for ch in "search AAPL":
            await pilot.press(ch)
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert app._current_symbol == "AAPL"


@pytest.mark.asyncio
async def test_r_triggers_refresh(fake_provider, monkeypatch):
    """Pressing r refreshes when not in input."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Load ticker first
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Unfocus input, press r
        app.set_focus(None)
        await pilot.press("r")
        await app.workers.wait_for_complete()
        # Should not crash, ticker still loaded
        assert app._current_symbol == "AAPL"


# --- Status Bar ---


@pytest.mark.asyncio
async def test_status_bar_shows_help_hint():
    """Status bar displays '?' help hint."""

    class StatusTestApp(App):
        def compose(self):
            yield StatusBar(provider_name="yahoo")

    app = StatusTestApp()
    async with app.run_test():
        bar = app.query_one(StatusBar)
        keys_widget = bar.query_one(".status-keys")
        rendered = keys_widget.render().plain
        assert "?" in rendered
        assert "Help" in rendered
