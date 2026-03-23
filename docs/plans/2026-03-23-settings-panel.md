# Settings Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen settings panel with vim-style commands for editing all config options in-app.

**Architecture:** New `SettingsScreen` (a Textual `Screen`) with a scrollable list of settings rows, a vim-style command input at the bottom, and a `save_config()` function for YAML persistence. The screen receives `AppConfig`, lets the user edit values, and returns the updated config via `dismiss()` callback for hot-apply.

**Tech Stack:** Python 3.11+, Textual (Screen, Static, Input, VerticalScroll), PyYAML

**Spec:** `docs/specs/2026-03-23-settings-panel-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/tenortui/config.py` | Add `fred_api_key` to `CONFIG_OPTIONS`, add `save_config()`, add section metadata |
| Create | `src/tenortui/widgets/settings_screen.py` | Full-screen settings UI with vim commands |
| Modify | `src/tenortui/app.py` | Add `,` keybinding, store `AppConfig`, push/callback settings screen, hot-apply |
| Modify | `src/tenortui/widgets/help_overlay.py` | Add `,` -> "Open settings" to keybindings list |
| Create | `tests/test_save_config.py` | Unit tests for `save_config()` |
| Create | `tests/test_settings_screen.py` | Pilot tests for settings screen UI |

---

### Task 1: Add `fred_api_key` to CONFIG_OPTIONS and add `save_config()`

**Files:**
- Modify: `src/tenortui/config.py:164-229` (CONFIG_OPTIONS list), append after line 228
- Modify: `src/tenortui/config.py` (add `save_config()` function after `load_config`)
- Test: `tests/test_save_config.py`

- [ ] **Step 1: Write failing tests for `save_config()`**

```python
# tests/test_save_config.py
import yaml
import pytest

from tenortui.config import save_config, load_config


class TestSaveConfig:
    def test_save_creates_new_file(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        save_config({"default": "tradier"}, config_path=config_path)
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert data["default"] == "tradier"

    def test_save_creates_parent_directories(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.yaml"
        save_config({"default": "yahoo"}, config_path=config_path)
        assert config_path.exists()

    def test_save_merges_with_existing(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("---\ndefault: yahoo\nspread_thresholds:\n  tight: 5.0\n  moderate: 15.0\n")
        save_config({"spread_thresholds": {"tight": 3.0}}, config_path=config_path)
        data = yaml.safe_load(config_path.read_text())
        assert data["default"] == "yahoo"
        assert data["spread_thresholds"]["tight"] == 3.0
        assert data["spread_thresholds"]["moderate"] == 15.0

    def test_save_deep_merges_nested(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("---\nyahoo:\n  greeks:\n    enabled: false\n    risk_free_rate: 0.05\n")
        save_config({"yahoo": {"greeks": {"enabled": True}}}, config_path=config_path)
        data = yaml.safe_load(config_path.read_text())
        assert data["yahoo"]["greeks"]["enabled"] is True
        assert data["yahoo"]["greeks"]["risk_free_rate"] == 0.05

    def test_save_roundtrip_with_load(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("---\ndefault: yahoo\nrefresh:\n  regular: 60\n")
        save_config({"refresh": {"regular": 30}}, config_path=config_path)
        config = load_config(config_path=config_path)
        assert config.refresh.regular == 30
        assert config.refresh.extended == 120  # default preserved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_save_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'save_config'`

- [ ] **Step 3: Implement `save_config()` and add `fred_api_key` to CONFIG_OPTIONS**

In `src/tenortui/config.py`, add `fred_api_key` entry to `CONFIG_OPTIONS` (after the last `ConfigOption` at line 228, before the closing `]`):

```python
    ConfigOption(
        key="fred_api_key",
        type_name="str",
        default="",
        description="FRED API key for fetching live risk-free rate. Optional.",
    ),
```

Add `save_config()` function after `load_config()` (after line 152):

```python
def save_config(changes: dict, config_path: Path | None = None) -> None:
    """Deep-merge *changes* into the config file and write it back."""
    if config_path is None:
        config_path = resolve_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_config_file(config_path) if config_path.exists() else {}
    _deep_merge(existing, changes)
    with open(config_path, "w") as f:
        yaml.safe_dump(existing, f, default_flow_style=False, sort_keys=False)


def _deep_merge(base: dict, overrides: dict) -> None:
    """Recursively merge overrides into base dict, mutating base."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_save_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/config.py tests/test_save_config.py
git commit -m "feat: add save_config() and fred_api_key to CONFIG_OPTIONS

Closes #4 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Build the SettingsScreen widget

**Files:**
- Create: `src/tenortui/widgets/settings_screen.py`
- Test: `tests/test_settings_screen.py`

This is the largest task. The screen has three modes: **navigation** (j/k to move, Enter to edit), **editing** (typing a new value, Enter to confirm, Esc to cancel), and **command** (`:` opens command input, Enter executes).

- [ ] **Step 1: Write failing test for basic screen rendering**

```python
# tests/test_settings_screen.py
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static, Input

from tenortui.config import AppConfig
from tenortui.widgets.settings_screen import SettingsScreen


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Prevent tests from reading/writing the real config file."""
    monkeypatch.setattr("tenortui.config.resolve_config_path", lambda: tmp_path / "config.yaml")


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
        # Title should be visible
        title = screen.query_one("#settings-title")
        assert "Settings" in title.render().plain
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run python -m pytest tests/test_settings_screen.py::test_settings_screen_renders -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement SettingsScreen skeleton**

```python
# src/tenortui/widgets/settings_screen.py
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Horizontal
from textual.message import Message
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Static, Input

from tenortui.config import (
    AppConfig,
    CONFIG_OPTIONS,
    KNOWN_PROVIDERS,
    save_config,
    resolve_config_path,
)

# Map config key prefixes to display section names
SECTION_MAP = {
    "default": "General",
    "spread_thresholds": "Spread Thresholds",
    "refresh": "Refresh Intervals",
    "yahoo": "Yahoo",
    "tradier": "Tradier",
    "fred_api_key": "Advanced",
}


def _section_for_key(key: str) -> str:
    """Determine the section name for a config key."""
    if key in SECTION_MAP:
        return SECTION_MAP[key]
    prefix = key.split(".")[0]
    return SECTION_MAP.get(prefix, "General")


def _get_current_value(config: AppConfig, key: str, raw_tradier: dict | None = None) -> str:
    """Extract the current value for a config key from AppConfig.

    raw_tradier is the tradier section from the raw YAML, used to read
    tradier settings regardless of which provider is active.
    """
    if key == "default":
        return config.provider_name
    elif key == "spread_thresholds.tight":
        return str(config.spread_thresholds.tight)
    elif key == "spread_thresholds.moderate":
        return str(config.spread_thresholds.moderate)
    elif key == "refresh.regular":
        return str(config.refresh.regular)
    elif key == "refresh.extended":
        return str(config.refresh.extended)
    elif key == "refresh.closed":
        return str(config.refresh.closed)
    elif key == "yahoo.greeks.enabled":
        return str(config.greeks.enabled).lower()
    elif key == "yahoo.greeks.risk_free_rate":
        return str(config.greeks.risk_free_rate)
    elif key == "tradier.api_key":
        tradier = raw_tradier or {}
        return tradier.get("api_key", "")
    elif key == "tradier.sandbox":
        tradier = raw_tradier or {}
        return str(tradier.get("sandbox", False)).lower()
    elif key == "fred_api_key":
        return config.fred_api_key or ""
    return ""


class SettingRow(Widget):
    """A single editable setting row."""

    DEFAULT_CSS = """
    SettingRow {
        layout: horizontal;
        height: 1;
        padding: 0 2;
    }
    SettingRow.focused {
        background: $accent 20%;
    }
    SettingRow.modified .setting-value {
        color: $warning;
    }
    SettingRow .setting-label {
        width: 30;
    }
    SettingRow .setting-value {
        width: 1fr;
    }
    SettingRow Input {
        width: 1fr;
        height: 1;
        border: none;
        padding: 0;
    }
    """

    def __init__(self, key: str, label: str, value: str, type_name: str) -> None:
        super().__init__()
        self.key = key
        self.label = label
        self.current_value = value
        self.original_value = value
        self.type_name = type_name
        self._editing = False

    @property
    def is_modified(self) -> bool:
        return self.current_value != self.original_value

    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="setting-label")
        yield Static(self._display_value(), classes="setting-value", id=f"val-{self.key}")

    def _display_value(self) -> str:
        if self.type_name == "bool":
            return "[x]" if self.current_value == "true" else "[ ]"
        if self.key == "tradier.api_key" and self.current_value:
            return "****" + self.current_value[-4:] if len(self.current_value) > 4 else "****"
        if not self.current_value:
            return "(not set)"
        return self.current_value

    def start_edit(self) -> None:
        """Enter edit mode for this row."""
        if self.type_name == "bool":
            # Toggle immediately
            self.current_value = "false" if self.current_value == "true" else "true"
            self._update_display()
            return
        if self.key == "default":
            # Cycle through providers
            providers = sorted(KNOWN_PROVIDERS)
            try:
                idx = providers.index(self.current_value)
                self.current_value = providers[(idx + 1) % len(providers)]
            except ValueError:
                self.current_value = providers[0]
            self._update_display()
            return
        # Text/number: show Input widget
        self._editing = True
        value_widget = self.query_one(f"#val-{self.key}", Static)
        value_widget.display = False
        edit_input = Input(
            value=self.current_value,
            id=f"edit-{self.key}",
        )
        self.mount(edit_input)
        edit_input.focus()

    def cancel_edit(self) -> None:
        """Cancel inline editing."""
        if not self._editing:
            return
        self._editing = False
        try:
            edit_input = self.query_one(f"#edit-{self.key}", Input)
            edit_input.remove()
        except Exception:
            pass
        self.query_one(f"#val-{self.key}", Static).display = True

    def confirm_edit(self, new_value: str) -> bool:
        """Confirm inline editing. Returns True if value is valid."""
        if not self._editing:
            return True
        # Validate
        if self.type_name == "int":
            try:
                val = int(new_value)
                if val <= 0:
                    return False
            except ValueError:
                return False
        elif self.type_name == "float":
            try:
                val = float(new_value)
                if val <= 0:
                    return False
            except ValueError:
                return False
        self._editing = False
        self.current_value = new_value
        try:
            edit_input = self.query_one(f"#edit-{self.key}", Input)
            edit_input.remove()
        except Exception:
            pass
        self.query_one(f"#val-{self.key}", Static).display = True
        self._update_display()
        return True

    def _update_display(self) -> None:
        self.query_one(f"#val-{self.key}", Static).update(self._display_value())
        if self.is_modified:
            self.add_class("modified")
        else:
            self.remove_class("modified")

    @property
    def is_editing(self) -> bool:
        return self._editing


class SettingsScreen(Screen):
    DEFAULT_CSS = """
    SettingsScreen {
        background: $surface;
    }
    SettingsScreen #settings-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 1 0;
        color: $accent;
    }
    SettingsScreen #settings-scroll {
        height: 1fr;
    }
    SettingsScreen .section-header {
        text-style: bold;
        padding: 1 2 0 2;
        color: $text;
    }
    SettingsScreen #cmd-bar {
        dock: bottom;
        height: 3;
        display: none;
        background: $surface;
    }
    SettingsScreen #cmd-bar Horizontal {
        height: 3;
        align: left middle;
    }
    SettingsScreen #cmd-bar .cmd-prefix {
        width: 2;
        color: $accent;
        padding: 1 0 0 1;
    }
    SettingsScreen #cmd-bar Input {
        width: 1fr;
        border: none;
    }
    SettingsScreen #settings-status {
        dock: bottom;
        height: 1;
        color: $text-muted;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "edit", "Edit", show=False),
        Binding("escape", "cancel_or_close", "Cancel/Close", show=False),
        Binding("colon", "open_command", "Command", show=False),
        Binding("comma", "close", "Close", show=False),
    ]

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._cursor_index = 0
        self._rows: list[SettingRow] = []
        self._command_mode = False
        self._saved = False  # Track if :w was used (for hot-apply on :q after :w)
        # Read raw YAML to get ALL provider configs, not just the active one.
        # AppConfig.provider_config only has the active provider's section.
        from tenortui.config import _read_config_file, resolve_config_path
        raw = _read_config_file(resolve_config_path())
        self._raw_tradier = raw.get("tradier", {}) if isinstance(raw.get("tradier"), dict) else {}
        self._raw_yahoo = raw.get("yahoo", {}) if isinstance(raw.get("yahoo"), dict) else {}

    def compose(self) -> ComposeResult:
        yield Static("Settings", id="settings-title")
        with VerticalScroll(id="settings-scroll"):
            current_section = ""
            for opt in CONFIG_OPTIONS:
                section = _section_for_key(opt.key)
                if section != current_section:
                    current_section = section
                    yield Static(f"  {section}", classes="section-header")
                value = _get_current_value(self._config, opt.key, raw_tradier=self._raw_tradier)
                label = opt.description.split(".")[0] if len(opt.key.split(".")) == 1 else opt.key.split(".")[-1].replace("_", " ").title()
                row = SettingRow(
                    key=opt.key,
                    label=label,
                    value=value,
                    type_name=opt.type_name,
                )
                self._rows.append(row)
                yield row
        yield Static("", id="settings-status")
        with Widget(id="cmd-bar"):
            with Horizontal():
                yield Static(":", classes="cmd-prefix")
                yield Input(id="settings-cmd-input")

    def on_mount(self) -> None:
        if self._rows:
            self._rows[0].add_class("focused")
        self._update_title()

    def _update_title(self) -> None:
        modified = any(r.is_modified for r in self._rows)
        title = "Settings [modified]" if modified else "Settings"
        self.query_one("#settings-title", Static).update(title)

    @property
    def _has_unsaved_changes(self) -> bool:
        return any(r.is_modified for r in self._rows)

    @property
    def _current_row(self) -> SettingRow | None:
        if 0 <= self._cursor_index < len(self._rows):
            return self._rows[self._cursor_index]
        return None

    def action_cursor_down(self) -> None:
        if self._command_mode or (self._current_row and self._current_row.is_editing):
            return
        if self._cursor_index < len(self._rows) - 1:
            self._rows[self._cursor_index].remove_class("focused")
            self._cursor_index += 1
            self._rows[self._cursor_index].add_class("focused")
            self._rows[self._cursor_index].scroll_visible()

    def action_cursor_up(self) -> None:
        if self._command_mode or (self._current_row and self._current_row.is_editing):
            return
        if self._cursor_index > 0:
            self._rows[self._cursor_index].remove_class("focused")
            self._cursor_index -= 1
            self._rows[self._cursor_index].add_class("focused")
            self._rows[self._cursor_index].scroll_visible()

    def action_edit(self) -> None:
        if self._command_mode:
            return
        row = self._current_row
        if row and not row.is_editing:
            row.start_edit()
            self._update_title()

    def action_cancel_or_close(self) -> None:
        if self._command_mode:
            self._close_command()
            return
        row = self._current_row
        if row and row.is_editing:
            row.cancel_edit()
            return
        # Esc in navigation mode — do nothing (use :q to quit)

    def action_open_command(self) -> None:
        row = self._current_row
        if row and row.is_editing:
            return
        self._command_mode = True
        cmd_bar = self.query_one("#cmd-bar")
        cmd_bar.display = True
        cmd_input = self.query_one("#settings-cmd-input", Input)
        cmd_input.value = ""
        self.call_after_refresh(cmd_input.focus)

    def action_close(self) -> None:
        """Handle , key — quit if not editing."""
        row = self._current_row
        if row and row.is_editing:
            return
        if self._command_mode:
            return
        self._try_quit()

    def _close_command(self) -> None:
        self._command_mode = False
        self.query_one("#cmd-bar").display = False

    def _execute_command(self, cmd: str) -> None:
        cmd = cmd.strip()
        if cmd == "wq":
            self._save_and_quit()
        elif cmd == "w":
            self._save()
        elif cmd == "q!":
            self.dismiss(None)
        elif cmd == "q":
            self._try_quit()
        else:
            self.query_one("#settings-status", Static).update(
                f"Unknown command: :{cmd}"
            )

    def _try_quit(self) -> None:
        if self._has_unsaved_changes:
            self.query_one("#settings-status", Static).update(
                "Unsaved changes. :q! to discard, :wq to save and quit."
            )
        elif self._saved:
            # :w was used earlier — dismiss with updated config for hot-apply
            self.dismiss(self._build_updated_config())
        else:
            self.dismiss(None)

    def _save(self) -> None:
        changes = self._build_changes_dict()
        save_config(changes)
        self._saved = True
        # Mark all rows as saved
        for row in self._rows:
            row.original_value = row.current_value
            row.remove_class("modified")
        self._update_title()
        status_msg = "Settings saved."
        if "default" in changes:
            status_msg += f" Provider changed to {changes['default']} — restart to apply."
        self.query_one("#settings-status", Static).update(status_msg)

    def _save_and_quit(self) -> None:
        changes = self._build_changes_dict()
        save_config(changes)
        config = self._build_updated_config()
        self.dismiss(config)

    def _build_changes_dict(self) -> dict:
        """Build a dict of only changed values for save_config()."""
        changes: dict = {}
        for row in self._rows:
            if not row.is_modified:
                continue
            key = row.key
            value = self._coerce_value(row.current_value, row.type_name)
            parts = key.split(".")
            target = changes
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value
        return changes

    def _build_updated_config(self) -> AppConfig:
        """Build an AppConfig reflecting all current values."""
        from tenortui.config import SpreadThresholds, GreeksConfig, RefreshConfig

        provider_name = self._get_row_value("default") or self._config.provider_name

        # Build provider_config for the selected provider
        if provider_name == "tradier":
            provider_config = {
                "api_key": self._get_row_value("tradier.api_key"),
                "sandbox": self._get_row_value("tradier.sandbox") == "true",
            }
        else:
            provider_config = dict(self._config.provider_config)

        return AppConfig(
            provider_name=provider_name,
            provider_config=provider_config,
            spread_thresholds=SpreadThresholds(
                tight=float(self._get_row_value("spread_thresholds.tight")),
                moderate=float(self._get_row_value("spread_thresholds.moderate")),
            ),
            greeks=GreeksConfig(
                enabled=self._get_row_value("yahoo.greeks.enabled") == "true",
                risk_free_rate=float(self._get_row_value("yahoo.greeks.risk_free_rate")),
            ),
            fred_api_key=self._get_row_value("fred_api_key") or None,
            refresh=RefreshConfig(
                regular=int(self._get_row_value("refresh.regular")),
                extended=int(self._get_row_value("refresh.extended")),
                closed=int(self._get_row_value("refresh.closed")),
            ),
        )

    def _get_row_value(self, key: str) -> str:
        for row in self._rows:
            if row.key == key:
                return row.current_value
        return ""

    @staticmethod
    def _coerce_value(value: str, type_name: str):
        if type_name == "bool":
            return value == "true"
        elif type_name == "int":
            return int(value)
        elif type_name == "float":
            return float(value)
        return value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "settings-cmd-input":
            cmd = event.value.strip()
            self._close_command()
            if cmd:
                self._execute_command(cmd)
        elif event.input.id and event.input.id.startswith("edit-"):
            # Inline edit confirmed
            key = event.input.id.removeprefix("edit-")
            for row in self._rows:
                if row.key == key:
                    if not row.confirm_edit(event.value):
                        self.query_one("#settings-status", Static).update(
                            f"Invalid value for {key}. Must be a positive {row.type_name}."
                        )
                        row.cancel_edit()
                    self._update_title()
                    break

    def on_key(self, event) -> None:
        """Block j/k/enter/colon bindings from firing during edit or command mode."""
        if self._command_mode:
            # Let Input handle all keys except escape
            if event.key == "escape":
                self._close_command()
                event.prevent_default()
                event.stop()
            elif event.key in ("j", "k", "colon", "comma"):
                event.prevent_default()
                event.stop()
            return
        row = self._current_row
        if row and row.is_editing:
            # Let Input handle all keys except escape
            if event.key == "escape":
                row.cancel_edit()
                event.prevent_default()
                event.stop()
            elif event.key in ("j", "k", "colon", "comma"):
                event.prevent_default()
                event.stop()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run python -m pytest tests/test_settings_screen.py::test_settings_screen_renders -v`
Expected: PASS

- [ ] **Step 5: Write tests for j/k navigation**

Add to `tests/test_settings_screen.py`:

```python
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
```

- [ ] **Step 6: Run navigation tests**

Run: `poetry run python -m pytest tests/test_settings_screen.py -v`
Expected: All PASS

- [ ] **Step 7: Write tests for bool toggle and enum cycle**

Add to `tests/test_settings_screen.py`:

```python
@pytest.mark.asyncio
async def test_enter_toggles_boolean():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        # Find the greeks.enabled row
        greeks_row = None
        for i, row in enumerate(screen._rows):
            if row.key == "yahoo.greeks.enabled":
                greeks_row = row
                # Move cursor to it
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
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        # First row should be "default" provider
        assert screen._rows[0].key == "default"
        assert screen._rows[0].current_value == "yahoo"
        await pilot.press("enter")
        await pilot.pause()
        assert screen._rows[0].current_value == "tradier"
```

- [ ] **Step 8: Run all settings screen tests**

Run: `poetry run python -m pytest tests/test_settings_screen.py -v`
Expected: All PASS

- [ ] **Step 9: Write tests for vim commands (:wq, :q!, :q with dirty state)**

Add to `tests/test_settings_screen.py`:

```python
@pytest.mark.asyncio
async def test_q_bang_discards_and_closes():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(app.screen, SettingsScreen)
        # Make a change
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
        # Make a change
        await pilot.press("enter")
        await pilot.pause()
        # :q (should warn, not close)
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press("q")
        await pilot.press("enter")
        await pilot.pause()
        # Should still be on settings screen
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
```

- [ ] **Step 10: Write tests for inline text/number editing and :w command**

Add to `tests/test_settings_screen.py`:

```python
@pytest.mark.asyncio
async def test_inline_number_editing():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        # Navigate to spread_thresholds.tight
        for i, row in enumerate(screen._rows):
            if row.key == "spread_thresholds.tight":
                for _ in range(i):
                    await pilot.press("j")
                break
        await pilot.press("enter")  # Start editing
        await pilot.pause()
        # Type new value
        edit_input = screen.query_one(f"#edit-spread_thresholds.tight", Input)
        edit_input.value = "3.0"
        await pilot.press("enter")  # Confirm
        await pilot.pause()
        assert row.current_value == "3.0"
        assert row.is_modified


@pytest.mark.asyncio
async def test_invalid_number_rejected():
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        # Navigate to refresh.regular (int type)
        for i, row in enumerate(screen._rows):
            if row.key == "refresh.regular":
                for _ in range(i):
                    await pilot.press("j")
                break
        original = row.current_value
        await pilot.press("enter")
        await pilot.pause()
        edit_input = screen.query_one(f"#edit-refresh.regular", Input)
        edit_input.value = "not_a_number"
        await pilot.press("enter")
        await pilot.pause()
        # Value should be unchanged
        assert row.current_value == original
        status = screen.query_one("#settings-status", Static)
        assert "Invalid" in status.render().plain


@pytest.mark.asyncio
async def test_w_saves_without_closing(tmp_path, monkeypatch):
    monkeypatch.setattr("tenortui.config.resolve_config_path", lambda: tmp_path / "config.yaml")
    app = SettingsApp()
    async with app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = app.screen
        # Make a change
        await pilot.press("enter")  # Toggle provider
        await pilot.pause()
        assert screen._has_unsaved_changes
        # :w
        await pilot.press("colon")
        await pilot.pause()
        await pilot.press("w")
        await pilot.press("enter")
        await pilot.pause()
        # Should still be on settings screen, but no unsaved changes
        assert isinstance(app.screen, SettingsScreen)
        assert not screen._has_unsaved_changes
        status = screen.query_one("#settings-status", Static)
        assert "saved" in status.render().plain.lower()
```

- [ ] **Step 11: Run all settings screen tests**

Run: `poetry run python -m pytest tests/test_settings_screen.py -v`
Expected: All PASS

- [ ] **Step 12: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 13: Commit**

```bash
git add src/tenortui/widgets/settings_screen.py tests/test_settings_screen.py
git commit -m "feat: add SettingsScreen with vim-style commands

Full-screen settings panel with j/k navigation, Enter to edit,
and :wq/:q!/:q/:w vim commands. Supports bool toggle, enum cycle,
and validated inline text/number editing.

Closes #4 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Integrate SettingsScreen into TenorTUI app

**Files:**
- Modify: `src/tenortui/app.py:37-43` (BINDINGS), `src/tenortui/app.py:45-73` (__init__), add new methods
- Modify: `src/tenortui/widgets/help_overlay.py:8-36` (KEYBINDINGS)
- Test: `tests/test_settings_screen.py` (add integration tests)

- [ ] **Step 1: Write failing integration test**

Add to `tests/test_settings_screen.py`:

```python
from tenortui.app import TenorTUI


@pytest.fixture
def tenor_app(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_comma_opens_settings_from_app(tenor_app):
    async with tenor_app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        assert isinstance(tenor_app.screen, SettingsScreen)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run python -m pytest tests/test_settings_screen.py::test_comma_opens_settings_from_app -v`
Expected: FAIL — no `,` binding in TenorTUI

- [ ] **Step 3: Add `,` binding, store AppConfig, implement push/callback**

In `src/tenortui/app.py`:

Add import at top:
```python
from tenortui.config import AppConfig
from tenortui.widgets.settings_screen import SettingsScreen
```

Add to `BINDINGS` (line ~43):
```python
Binding("comma", "open_settings", "Settings", show=False),
```

Modify `__init__` signature to accept an optional `app_config` parameter:
```python
def __init__(
    self,
    provider,
    spread_thresholds: SpreadThresholds | None = None,
    greeks_config: GreeksConfig | None = None,
    fred_api_key: str | None = None,
    refresh_config: RefreshConfig | None = None,
    app_config: AppConfig | None = None,
):
    # ... existing code unchanged ...
    # Add at the end of __init__:
    self._app_config = app_config or AppConfig(
        provider_name=getattr(provider, "name", "yahoo"),
        spread_thresholds=self._spread_thresholds,
        greeks=self._greeks_config,
        fred_api_key=fred_api_key,
        refresh=self._refresh_config,
    )
```

In `main()` (line ~436), pass the full config object:
```python
app = TenorTUI(
    provider=provider,
    spread_thresholds=config.spread_thresholds,
    greeks_config=config.greeks,
    fred_api_key=config.fred_api_key,
    refresh_config=config.refresh,
    app_config=config,
)
```

Add methods to TenorTUI class:
```python
def action_open_settings(self) -> None:
    self._stop_auto_refresh()
    self.push_screen(SettingsScreen(self._app_config), callback=self._on_settings_closed)

def _on_settings_closed(self, result: AppConfig | None) -> None:
    if result is not None:
        old_config = self._app_config
        self._spread_thresholds = result.spread_thresholds
        self._refresh_config = result.refresh
        self._greeks_config = result.greeks
        self._app_config = result
        # Re-fetch risk-free rate if FRED API key changed
        if result.fred_api_key != old_config.fred_api_key:
            from tenortui.risk_free_rate import get_risk_free_rate
            rate, is_live = get_risk_free_rate(
                fallback=result.greeks.risk_free_rate,
                fred_api_key=result.fred_api_key,
            )
            self._risk_free_rate = rate
            self._risk_free_rate_is_live = is_live
            self.query_one(StatusBar).update_rate_display(rate, is_live)
        # Re-render chain with new settings if we have data loaded
        if self._current_symbol and self._current_expiration:
            self._load_chain(self._current_symbol, self._current_expiration)
    if self._auto_refresh_enabled and self._current_symbol:
        self._start_auto_refresh()
```

- [ ] **Step 4: Run integration test**

Run: `poetry run python -m pytest tests/test_settings_screen.py::test_comma_opens_settings_from_app -v`
Expected: PASS

- [ ] **Step 5: Write test for hot-apply callback**

Add to `tests/test_settings_screen.py`:

```python
@pytest.mark.asyncio
async def test_wq_saves_and_hot_applies(tenor_app, tmp_path, monkeypatch):
    monkeypatch.setattr("tenortui.config.resolve_config_path", lambda: tmp_path / "config.yaml")
    async with tenor_app.run_test() as pilot:
        await pilot.press("comma")
        await pilot.pause()
        screen = tenor_app.screen
        # Navigate to spread_thresholds.tight and toggle something simple — toggle greeks
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
        # Should be back on main screen with updated config
        assert not isinstance(tenor_app.screen, SettingsScreen)
        assert tenor_app._greeks_config.enabled is True
```

- [ ] **Step 6: Run all tests**

Run: `poetry run python -m pytest tests/test_settings_screen.py -v`
Expected: All PASS

- [ ] **Step 7: Update help overlay**

In `src/tenortui/widgets/help_overlay.py`, add to the "Panels" section (line ~33):
```python
(",", "Open settings"),
```

- [ ] **Step 8: Add `settings` command to command palette handler**

In `src/tenortui/app.py`, in `on_command_palette_command_submitted` (line ~259), add:
```python
elif cmd == "settings":
    self.action_open_settings()
```

- [ ] **Step 9: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 10: Lint and format**

Run: `poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 11: Commit**

```bash
git add src/tenortui/app.py src/tenortui/widgets/help_overlay.py tests/test_settings_screen.py
git commit -m "feat: integrate SettingsScreen into TenorTUI

Comma keybinding opens settings, :wq saves and hot-applies
non-restart settings (thresholds, refresh, greeks). Auto-refresh
paused while in settings. Help overlay and command palette updated.

Closes #4

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Final verification and cleanup

**Files:**
- All modified files

- [ ] **Step 1: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Lint and format**

Run: `poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 3: Manual smoke test**

Run: `poetry run tenortui`
- Press `,` — settings screen should appear
- Press `j`/`k` — cursor moves between rows
- Press `Enter` on a boolean — toggles
- Press `Enter` on provider — cycles
- Press `:wq` — saves and returns to main screen
- Press `,` again, then `:q!` — returns without saving

- [ ] **Step 4: Verify config file written**

Check `~/.config/tenor/config.yaml` reflects saved changes.
