"""Tests for vim-style keyboard navigation, help overlay, and command palette."""

import pytest
from textual.app import App, ComposeResult

from tenortui.widgets.help_overlay import HelpOverlay


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
