# Vim-style Keyboard Navigation + Help Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add vim-inspired keyboard navigation (j/k, h/l, g/G), a help overlay (?), a command palette (:), pane switching, and a `? for help` status bar hint across the TUI.

**Architecture:** Keybindings are handled at the app level via `on_key` to intercept vim keys before widgets consume them. A `HelpOverlay` modal screen shows context-aware bindings. A `CommandPalette` input widget appears at the bottom of the screen. The app tracks the "active pane" concept for pane-switching with tab/number keys. When the search input is focused, vim keys pass through to allow typing.

**Tech Stack:** Textual (ModalScreen, Screen.push_screen, on_key, DataTable cursor API, ListView index)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/tenortui/widgets/help_overlay.py` | Create | Modal screen showing context-aware keybinding cheat sheet |
| `src/tenortui/widgets/command_palette.py` | Create | Bottom-bar input widget for `:` commands |
| `src/tenortui/app.py` | Modify | Add vim keybindings, pane tracking, help/command integration |
| `src/tenortui/widgets/status_bar.py` | Modify | Add `? for help` hint |
| `src/tenortui/styles/app.tcss` | Modify | Styles for help overlay and command palette |
| `tests/test_vim_nav.py` | Create | Tests for vim navigation, pane switching, help overlay, command palette |

---

### Task 1: Help Overlay Widget

Create a modal screen that displays all keybindings in a readable format. Toggled with `?`.

**Files:**
- Create: `src/tenortui/widgets/help_overlay.py`
- Test: `tests/test_vim_nav.py`

- [ ] **Step 1: Write failing test for HelpOverlay**

```python
# tests/test_vim_nav.py
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
    """Help overlay opens with action and closes with ? or escape."""
    app = HelpTestApp()
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        assert len(app.screen_stack) == 2  # main + overlay

        await pilot.press("escape")
        assert len(app.screen_stack) == 1  # back to main
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vim_nav.py::test_help_overlay_opens_and_closes -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenortui.widgets.help_overlay'`

- [ ] **Step 3: Implement HelpOverlay**

```python
# src/tenortui/widgets/help_overlay.py
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static


KEYBINDINGS = [
    ("Navigation", [
        ("j / k", "Move down / up in lists and tables"),
        ("h / l", "Switch to previous / next pane"),
        ("g", "Jump to top of list"),
        ("G", "Jump to bottom of list"),
        ("Tab / Shift+Tab", "Next / previous pane"),
    ]),
    ("Actions", [
        ("/ or s", "Focus search bar"),
        ("r", "Refresh current data"),
        ("Enter", "Select / expand"),
        ("q", "Quit"),
    ]),
    ("Panels", [
        ("?", "Toggle this help overlay"),
        (":", "Open command palette"),
    ]),
]


class HelpOverlay(ModalScreen):
    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }
    HelpOverlay #help-container {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    HelpOverlay .help-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    HelpOverlay .help-section {
        text-style: bold;
        padding: 1 0 0 0;
        color: $text;
    }
    HelpOverlay .help-row {
        padding: 0 0 0 2;
        color: $text-muted;
    }
    HelpOverlay .help-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-container"):
            yield Static("Keyboard Shortcuts", classes="help-title")
            for section_name, bindings in KEYBINDINGS:
                yield Static(f"  {section_name}", classes="help-section")
                for key, desc in bindings:
                    yield Static(f"    {key:<20} {desc}", classes="help-row")
            yield Static("Press ? or Esc to close", classes="help-footer")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vim_nav.py::test_help_overlay_opens_and_closes -v`
Expected: PASS

- [ ] **Step 5: Write test for help overlay content**

```python
@pytest.mark.asyncio
async def test_help_overlay_shows_keybindings():
    """Help overlay displays keybinding sections."""
    app = HelpTestApp()
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        screen = app.screen
        text = screen.query_one("#help-container").render()
        # Verify key sections exist by checking Static widgets
        statics = screen.query(".help-section")
        section_texts = [s.render().plain for s in statics]
        assert any("Navigation" in t for t in section_texts)
        assert any("Actions" in t for t in section_texts)
```

- [ ] **Step 6: Run test, verify it passes**

Run: `python -m pytest tests/test_vim_nav.py::test_help_overlay_shows_keybindings -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/widgets/help_overlay.py tests/test_vim_nav.py
git commit -m "feat: add HelpOverlay modal screen with keybinding cheat sheet"
```

---

### Task 2: Command Palette Widget

A text input that appears at the bottom of the screen when `:` is pressed. Supports simple commands and dismisses with Escape or Enter.

**Files:**
- Create: `src/tenortui/widgets/command_palette.py`
- Test: `tests/test_vim_nav.py`

- [ ] **Step 1: Write failing test for CommandPalette**

```python
from tenortui.widgets.command_palette import CommandPalette


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
```

- [ ] **Step 2: Run test, verify it fails**

- [ ] **Step 3: Implement CommandPalette**

```python
# src/tenortui/widgets/command_palette.py
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static


class CommandPalette(Widget):
    DEFAULT_CSS = """
    CommandPalette {
        dock: bottom;
        height: 1;
        display: none;
        background: $surface;
    }
    CommandPalette Horizontal {
        height: 1;
    }
    CommandPalette .cmd-prefix {
        width: 2;
        color: $accent;
        padding: 0 0 0 1;
    }
    CommandPalette Input {
        width: 1fr;
        border: none;
        height: 1;
        padding: 0;
    }
    """

    class CommandSubmitted(Message):
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(":", classes="cmd-prefix")
            yield Input(id="cmd-input")

    def open(self) -> None:
        self.display = True
        self.query_one("#cmd-input", Input).value = ""
        self.query_one("#cmd-input", Input).focus()

    def close(self) -> None:
        self.display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if command:
            self.post_message(self.CommandSubmitted(command))
        self.close()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.close()
            event.prevent_default()
            event.stop()
```

- [ ] **Step 4: Run test, verify it passes**

- [ ] **Step 5: Write test for command submission**

```python
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
```

- [ ] **Step 6: Run test, verify it passes**

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/widgets/command_palette.py tests/test_vim_nav.py
git commit -m "feat: add CommandPalette widget with : prefix input"
```

---

### Task 3: Vim Navigation in App (j/k, g/G, pane switching)

Wire up vim keybindings in the main app. The key insight: intercept keys via `on_key` at the app level, but **only when the search input and command palette are not focused** (so typing isn't disrupted).

**Files:**
- Modify: `src/tenortui/app.py`
- Test: `tests/test_vim_nav.py`

- [ ] **Step 1: Write failing test for j/k navigation**

```python
from tenortui.app import TenorTUI
from tenortui.widgets.chain_table import ChainTable


@pytest.mark.asyncio
async def test_j_k_navigation_in_chain_table(fake_provider, monkeypatch):
    """j/k moves cursor in chain table DataTable."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Load ticker to populate chain table
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Focus chain table area (press escape to unfocus input)
        await pilot.press("escape")

        # j should move cursor down
        await pilot.press("j")
        # Should not crash — verifies j is handled
```

- [ ] **Step 2: Run test, verify it fails (j not handled)**

- [ ] **Step 3: Add vim key handling to app.py**

Update `app.py` to:
1. Import the new widgets
2. Add `HelpOverlay` and `CommandPalette` integration
3. Add `on_key` handler for j/k/g/G/h/l
4. Track active pane for pane switching
5. Add new BINDINGS for `?` and `:`

Key code to add to `TenorTUI`:

```python
# New imports
from tenortui.widgets.help_overlay import HelpOverlay
from tenortui.widgets.command_palette import CommandPalette

# Updated BINDINGS
BINDINGS = [
    ("q", "quit", "Quit"),
    ("slash", "focus_search", "Search"),
    ("s", "focus_search", "Search"),
    ("ctrl+r", "refresh", "Refresh"),
    ("r", "refresh", "Refresh"),
    ("question_mark", "help", "Help"),
    ("colon", "command_palette", "Command"),
]

# Add CommandPalette to compose()
def compose(self) -> ComposeResult:
    yield TickerBar()
    with Vertical(id="main-content"):
        yield ExpirySelector()
        yield RecentlyViewed(symbols=self._history)
        yield ChainTable()
    yield StatusBar(provider_name=self._provider.name)
    yield CommandPalette()

# New methods
def action_help(self) -> None:
    self.push_screen(HelpOverlay())

def action_command_palette(self) -> None:
    self.query_one(CommandPalette).open()

def _input_has_focus(self) -> bool:
    """Check if any text input widget has focus."""
    focused = self.focused
    if focused is None:
        return False
    from textual.widgets import Input
    return isinstance(focused, Input)

def on_key(self, event) -> None:
    """Handle vim-style navigation keys when no input is focused."""
    if self._input_has_focus():
        return

    from textual.widgets import DataTable, ListView
    key = event.key

    # j/k — move cursor down/up in focused DataTable or ListView
    if key == "j":
        if isinstance(self.focused, DataTable):
            self.focused.action_cursor_down()
            event.prevent_default()
        elif isinstance(self.focused, ListView):
            self.focused.action_cursor_down()
            event.prevent_default()
    elif key == "k":
        if isinstance(self.focused, DataTable):
            self.focused.action_cursor_up()
            event.prevent_default()
        elif isinstance(self.focused, ListView):
            self.focused.action_cursor_up()
            event.prevent_default()
    # g/G — jump to top/bottom
    elif key == "g":
        if isinstance(self.focused, DataTable):
            self.focused.move_cursor(row=0)
            event.prevent_default()
        elif isinstance(self.focused, ListView):
            self.focused.index = 0
            event.prevent_default()
    elif key == "G":
        if isinstance(self.focused, DataTable):
            self.focused.move_cursor(row=self.focused.row_count - 1)
            event.prevent_default()
        elif isinstance(self.focused, ListView):
            count = len(self.focused.children)
            if count > 0:
                self.focused.index = count - 1
            event.prevent_default()
    # h/l — switch panes (previous/next focusable)
    elif key == "l":
        self.action_focus_next()
        event.prevent_default()
    elif key == "h":
        self.action_focus_previous()
        event.prevent_default()

def on_command_palette_command_submitted(self, event: CommandPalette.CommandSubmitted) -> None:
    """Handle commands from the command palette."""
    cmd = event.command.lower().strip()
    if cmd == "q" or cmd == "quit":
        self.exit()
    elif cmd == "help":
        self.action_help()
    elif cmd.startswith("search ") or cmd.startswith("s "):
        parts = cmd.split(None, 1)
        if len(parts) == 2:
            symbol = parts[1].strip().upper()
            self._current_symbol = symbol
            self._load_ticker(symbol)
```

- [ ] **Step 4: Run test, verify it passes**

- [ ] **Step 5: Write test for help overlay via ? key**

```python
@pytest.mark.asyncio
async def test_help_overlay_via_question_mark(fake_provider, monkeypatch):
    """Pressing ? opens the help overlay."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        await pilot.press("escape")  # unfocus input
        await pilot.press("question_mark")
        assert len(app.screen_stack) == 2
```

- [ ] **Step 6: Write test for command palette via : key**

```python
@pytest.mark.asyncio
async def test_command_palette_via_colon(fake_provider, monkeypatch):
    """Pressing : opens the command palette."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        await pilot.press("escape")  # unfocus input
        await pilot.press("colon")
        palette = app.query_one(CommandPalette)
        assert palette.display is True
```

- [ ] **Step 7: Write test for vim keys ignored when input focused**

```python
@pytest.mark.asyncio
async def test_vim_keys_ignored_when_input_focused(fake_provider, monkeypatch):
    """j/k keys pass through to input when search is focused."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Input should have focus on launch
        from tenortui.widgets.ticker_bar import TickerBar
        input_w = app.query_one(TickerBar).query_one("#ticker-input")
        assert input_w.has_focus
        # j should be typed into input, not navigate
        await pilot.press("j")
        assert input_w.value == "j"
```

- [ ] **Step 8: Write test for command palette search command**

```python
@pytest.mark.asyncio
async def test_command_palette_search(fake_provider, monkeypatch):
    """':search AAPL' loads the ticker."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        await pilot.press("escape")
        await pilot.press("colon")
        await pilot.press(*"search AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        assert app._current_symbol == "AAPL"
```

- [ ] **Step 9: Run all tests, verify they pass**

Run: `python -m pytest tests/test_vim_nav.py -v`

- [ ] **Step 10: Commit**

```bash
git add src/tenortui/app.py tests/test_vim_nav.py
git commit -m "feat: add vim-style j/k/g/G/h/l navigation and command palette integration"
```

---

### Task 4: Status Bar Help Hint

Add `? for help` to the status bar.

**Files:**
- Modify: `src/tenortui/widgets/status_bar.py`
- Test: `tests/test_vim_nav.py`

- [ ] **Step 1: Write failing test**

```python
from tenortui.widgets.status_bar import StatusBar

@pytest.mark.asyncio
async def test_status_bar_shows_help_hint():
    """Status bar displays '? for help' hint."""
    class StatusTestApp(App):
        def compose(self):
            yield StatusBar(provider_name="yahoo")

    app = StatusTestApp()
    async with app.run_test():
        bar = app.query_one(StatusBar)
        keys_widget = bar.query_one(".status-keys")
        rendered = keys_widget.render().plain
        assert "?" in rendered
```

- [ ] **Step 2: Run test, verify it fails**

- [ ] **Step 3: Update StatusBar**

Change the keys static text in `status_bar.py`:

```python
yield Static("? Help | / Search | r Refresh | : Command | q Quit", classes="status-keys")
```

- [ ] **Step 4: Run test, verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/status_bar.py tests/test_vim_nav.py
git commit -m "feat: add help hint and updated keybindings to status bar"
```

---

### Task 5: Final Integration, Lint, and Coverage

Run full test suite, fix lint issues, ensure coverage threshold is met.

**Files:**
- All modified files

- [ ] **Step 1: Run full test suite with coverage**

Run: `python -m pytest -v --cov=tenortui --cov-report=term-missing --cov-fail-under=90`

- [ ] **Step 2: Fix any lint issues**

Run: `ruff check src/ tests/ && ruff format src/ tests/`

- [ ] **Step 3: Run tests again after lint fixes**

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: lint and format vim navigation code"
```

- [ ] **Step 5: Push and create PR**

```bash
git push -u origin worktree-vim-keyboard-nav
gh pr create --title "feat: vim-style keyboard navigation + help overlay" \
  --body "Closes #1"
```
