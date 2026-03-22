"""Tests for help overlay scrolling with j/k/g/G keys."""

import pytest
from textual.app import App, ComposeResult

from tenortui.widgets.help_overlay import HelpOverlay


class HelpScrollApp(App):
    BINDINGS = [("question_mark", "help", "Help")]

    def compose(self) -> ComposeResult:
        yield from ()

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())


@pytest.mark.asyncio
async def test_j_scrolls_down():
    """Pressing j scrolls the help overlay down."""
    app = HelpScrollApp()
    async with app.run_test(size=(80, 10)) as pilot:
        await pilot.press("question_mark")
        container = app.screen.query_one("#help-container")
        assert container.scroll_offset.y == 0
        await pilot.press("j")
        await pilot.pause()
        assert container.scroll_offset.y > 0


@pytest.mark.asyncio
async def test_k_scrolls_up():
    """Pressing k scrolls the help overlay up."""
    app = HelpScrollApp()
    async with app.run_test(size=(80, 10)) as pilot:
        await pilot.press("question_mark")
        container = app.screen.query_one("#help-container")
        # Scroll down first so we can scroll back up
        await pilot.press("j")
        await pilot.press("j")
        await pilot.pause()
        scrolled = container.scroll_offset.y
        await pilot.press("k")
        await pilot.pause()
        assert container.scroll_offset.y < scrolled


@pytest.mark.asyncio
async def test_g_scrolls_to_top():
    """Pressing g scrolls the help overlay to the top."""
    app = HelpScrollApp()
    async with app.run_test(size=(80, 10)) as pilot:
        await pilot.press("question_mark")
        container = app.screen.query_one("#help-container")
        # Scroll down first
        await pilot.press("j")
        await pilot.press("j")
        await pilot.press("j")
        await pilot.pause()
        assert container.scroll_offset.y > 0
        await pilot.press("g")
        await pilot.pause()
        assert container.scroll_offset.y == 0


@pytest.mark.asyncio
async def test_G_scrolls_to_bottom():
    """Pressing G scrolls the help overlay to the bottom."""
    app = HelpScrollApp()
    async with app.run_test(size=(80, 10)) as pilot:
        await pilot.press("question_mark")
        container = app.screen.query_one("#help-container")
        await pilot.press("G")
        await pilot.pause()
        assert container.scroll_offset.y > 0
        max_y = container.virtual_size.height - container.size.height
        assert container.scroll_offset.y >= max_y
