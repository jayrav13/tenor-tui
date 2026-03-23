# Settings Panel Design

## Summary

Add a full-screen settings panel to TenorTUI, accessible via `,` keybinding, allowing users to view and edit all configuration options without manually editing YAML files. Uses vim-style commands for save/quit operations.

## Decisions

- **Full screen** (not modal overlay) — establishes a pattern for future "pages" (e.g., stock-specific views)
- **Explicit save** with vim commands (`:wq`, `:w`, `:q`, `:q!`) — safer for settings with side effects
- **All settings editable in-app** — including API keys and credentials (already stored in plaintext YAML)
- **Provider changes require restart** — hot-swapping providers is a larger lift deferred for later
- **Flat scrollable list** with section headers — only ~11 settings, tabs would be overkill
- **Custom form widgets** (Approach A) — full control over vim-style keybindings without fighting Textual's built-in widget opinions
- **All provider settings always visible** — both Yahoo and Tradier sections shown regardless of active provider, so users can configure before switching
- **YAML comment loss accepted** — `yaml.safe_dump` will reformat the file; this is acceptable given the settings panel replaces manual editing

## Screen & Navigation

`SettingsScreen` is a `Screen` subclass pushed via `,` from the main app.

### Layout

```
+------------------------------------------+
|              Settings                     |
+------------------------------------------+
|                                           |
|  General                                  |
|    Default provider        yahoo          |
|                                           |
|  Spread Thresholds                        |
|    Tight                   5.0            |
|    Moderate                15.0           |
|                                           |
|  Refresh Intervals                        |
|    Regular (seconds)       60             |
|    Extended (seconds)      120            |
|    Closed (seconds)        300            |
|                                           |
|  Yahoo                                    |
|    Greeks enabled          [ ]            |
|    Risk-free rate          0.05           |
|                                           |
|  Tradier                                  |
|    API key                 ****           |
|    Sandbox                 [ ]            |
|                                           |
|  Advanced                                 |
|    FRED API key            (not set)      |
|                                           |
+------------------------------------------+
|  :                                        |
+------------------------------------------+
```

### Keybindings

| Key | Action |
|-----|--------|
| `j` / `k` | Move cursor between setting rows |
| `Enter` | Edit focused setting (inline edit for text/numbers, toggle for booleans, cycle for enums) |
| `Esc` | Cancel inline edit |
| `:wq` | Save and quit |
| `:w` | Save (stay on screen) |
| `:q` | Quit (warns if unsaved changes) |
| `:q!` | Quit discarding unsaved changes |
| `,` | Quit (same as `:q`), only in navigation mode — ignored during inline edit |

## Settings Display & Editing

Each setting row: `label    current_value`

### Edit behavior by type

- **Booleans** (`greeks.enabled`, `tradier.sandbox`): Toggle on Enter. Display as `[x]` / `[ ]`.
- **Strings** (`tradier.api_key`, `fred_api_key`): Enter opens an inline `Input` widget replacing the value. Esc cancels, Enter confirms.
- **Numbers** (`spread_thresholds.tight`, `refresh.regular`, etc.): Same as strings, validated as int/float on confirm. Invalid input shows brief error, keeps old value. Must be positive.
- **Enum** (`default` provider): Cycles through known values on Enter (yahoo -> tradier -> yahoo). Enum values sourced from `KNOWN_PROVIDERS` set in config.py.

### Section grouping

Settings are grouped into sections derived from the `ConfigOption.key` prefix. The mapping:
- No prefix / `default` -> "General"
- `spread_thresholds.*` -> "Spread Thresholds"
- `refresh.*` -> "Refresh Intervals"
- `yahoo.*` -> "Yahoo"
- `tradier.*` -> "Tradier"
- `fred_api_key` -> "Advanced"

Section headers are non-focusable `Static` widgets — cursor skips them.

### Visual indicators

- Modified values highlighted in a distinct color.
- Title bar shows `Settings [modified]` when there are unsaved changes.

## Config Persistence

### Prerequisites

Add a `ConfigOption` entry for `fred_api_key` to the `CONFIG_OPTIONS` registry in `config.py`, so the settings panel has metadata for all editable fields.

### `save_config()` function

New function in `config.py`:

1. Reads existing YAML via `_read_config_file()` to get the raw dict.
2. Deep-merges only changed values into the dict.
3. Creates parent directories if they don't exist (`Path.mkdir(parents=True, exist_ok=True)`).
4. Writes back via `yaml.safe_dump()` to the resolved config path.
5. Note: `yaml.safe_dump` will reformat the file — comments and custom formatting will be lost. This is acceptable since the settings panel is the primary editing interface.

The settings screen tracks a dict of **only changed values** and passes it to `save_config()`.

### Provider change handling

After save, if provider changed, display: "Provider changed to {name} — restart to apply."

### Unsaved changes protection

On `:q` with unsaved changes, the command bar shows: "Unsaved changes. :q! to discard, :wq to save and quit."

## App Integration

- `,` keybinding added to `TenorTUI.BINDINGS`, calls `self.push_screen(SettingsScreen(self._app_config), callback=self._on_settings_closed)`.
- `SettingsScreen.__init__` receives the current `AppConfig`.
- On `:wq`/`:w`, the screen calls `self.dismiss(updated_config)` returning the new `AppConfig`.
- On `:q`/`:q!`, the screen calls `self.dismiss(None)`.
- `_on_settings_closed(result)` in `TenorTUI` receives the callback:
  - If `result` is `None`, no action.
  - If `result` is an `AppConfig`, hot-apply the non-restart settings:
    - **Spread thresholds**: update `self._spread_thresholds`, re-render current chain if loaded.
    - **Refresh intervals**: update `self._refresh_config`, restart auto-refresh timer with new interval.
    - **Greeks config**: update `self._greeks_config`. If toggled on, trigger a chain reload to calculate Greeks. If toggled off, reload chain without Greeks.
    - **FRED API key**: update `self._fred_api_key`, re-fetch risk-free rate via `get_risk_free_rate()`.
  - If provider changed, show status message (no runtime change).
- Help overlay updated: `,` -> "Open settings" in Panels section.
- Command palette gets a `settings` command (opens settings screen, same as `,`).
- Auto-refresh paused while settings screen is open; resumed on close.
- Workers in progress are not cancelled — settings screen simply overlays them. Any in-flight results apply normally when the screen is popped.

### Storing AppConfig on the app

`TenorTUI` currently stores config fields as separate instance attributes. Add a `self._app_config` reference to the full `AppConfig` passed at init, so it can be forwarded to the settings screen.

## Testing

- **`save_config()` unit tests**: round-trip read -> modify -> write -> read, verify values. Test with missing config file (creates new). Test with existing file (merges correctly). Test parent directory creation.
- **Settings screen pilot tests**: j/k navigation (skips headers), Enter editing for each type (bool toggle, string input, number validation with invalid input, enum cycle), vim commands (:wq saves and dismisses, :q! discards, :q with dirty state shows warning, :w saves without dismissing), `,` quits in navigation mode.
- **Integration test**: hot-apply of non-restart settings (e.g., change spread threshold via settings screen, verify app's `_spread_thresholds` updated and chain re-rendered).
