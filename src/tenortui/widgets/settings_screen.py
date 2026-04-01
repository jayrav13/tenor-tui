from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Input, Static

from tenortui.config import (
    AppConfig,
    CONFIG_OPTIONS,
    KNOWN_PROVIDERS,
    GreeksConfig,
    RefreshConfig,
    SpreadThresholds,
    _read_config_file,
    resolve_config_path,
    save_config,
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


def _get_current_value(
    config: AppConfig, key: str, raw_tradier: dict | None = None
) -> str:
    """Extract the current value for a config key from AppConfig."""
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


def _safe_id(key: str) -> str:
    """Convert a config key to a valid Textual widget ID."""
    return key.replace(".", "-")


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
        yield Static(
            self._display_value(),
            classes="setting-value",
            id=f"val-{_safe_id(self.key)}",
        )

    def _display_value(self) -> str:
        if self.type_name == "bool":
            return "[x]" if self.current_value == "true" else "[ ]"
        if self.key == "tradier.api_key" and self.current_value:
            if len(self.current_value) > 4:
                return "****" + self.current_value[-4:]
            return "****"
        if not self.current_value:
            return "(not set)"
        return self.current_value

    def start_edit(self) -> None:
        """Enter edit mode for this row."""
        if self.type_name == "bool":
            self.current_value = "false" if self.current_value == "true" else "true"
            self._update_display()
            return
        if self.key == "default":
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
        value_widget = self.query_one(f"#val-{_safe_id(self.key)}", Static)
        value_widget.display = False
        edit_input = Input(
            value=self.current_value,
            id=f"edit-{_safe_id(self.key)}",
        )
        self.mount(edit_input)
        edit_input.focus()

    def cancel_edit(self) -> None:
        """Cancel inline editing."""
        if not self._editing:
            return
        self._editing = False
        try:
            edit_input = self.query_one(f"#edit-{_safe_id(self.key)}", Input)
            edit_input.remove()
        except Exception:
            pass
        self.query_one(f"#val-{_safe_id(self.key)}", Static).display = True

    def confirm_edit(self, new_value: str) -> bool:
        """Confirm inline editing. Returns True if value is valid."""
        if not self._editing:
            return True
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
            edit_input = self.query_one(f"#edit-{_safe_id(self.key)}", Input)
            edit_input.remove()
        except Exception:
            pass
        self.query_one(f"#val-{_safe_id(self.key)}", Static).display = True
        self._update_display()
        return True

    def _update_display(self) -> None:
        self.query_one(f"#val-{_safe_id(self.key)}", Static).update(
            self._display_value()
        )
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
        self._saved = False
        raw = _read_config_file(resolve_config_path())
        self._raw_tradier = (
            raw.get("tradier", {}) if isinstance(raw.get("tradier"), dict) else {}
        )

    def compose(self) -> ComposeResult:
        yield Static("Settings", id="settings-title")
        with VerticalScroll(id="settings-scroll"):
            current_section = ""
            for opt in CONFIG_OPTIONS:
                section = _section_for_key(opt.key)
                if section != current_section:
                    current_section = section
                    yield Static(f"  {section}", classes="section-header")
                value = _get_current_value(
                    self._config, opt.key, raw_tradier=self._raw_tradier
                )
                label = (
                    opt.description.split(".")[0]
                    if len(opt.key.split(".")) == 1
                    else opt.key.split(".")[-1].replace("_", " ").title()
                )
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
        title = "Settings \\[modified]" if modified else "Settings"
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
        """Handle , key -- quit if not editing."""
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
            self.dismiss(self._build_updated_config())
        else:
            self.dismiss(None)

    def _save(self) -> None:
        changes = self._build_changes_dict()
        save_config(changes)
        self._saved = True
        for row in self._rows:
            row.original_value = row.current_value
            row.remove_class("modified")
        self._update_title()
        status_msg = "Settings saved."
        if "default" in changes:
            status_msg += (
                f" Provider changed to {changes['default']} — restart to apply."
            )
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
        provider_name = self._get_row_value("default") or self._config.provider_name

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
                risk_free_rate=float(
                    self._get_row_value("yahoo.greeks.risk_free_rate")
                ),
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
            safe_key = event.input.id.removeprefix("edit-")
            for row in self._rows:
                if _safe_id(row.key) == safe_key:
                    if not row.confirm_edit(event.value):
                        self.query_one("#settings-status", Static).update(
                            f"Invalid value for {row.key}. Must be a positive {row.type_name}."
                        )
                        row.cancel_edit()
                    self._update_title()
                    break

    def on_key(self, event) -> None:
        """Block j/k/enter/colon bindings from firing during edit or command mode."""
        if self._command_mode:
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
            if event.key == "escape":
                row.cancel_edit()
                event.prevent_default()
                event.stop()
            elif event.key in ("j", "k", "colon", "comma"):
                event.prevent_default()
                event.stop()
