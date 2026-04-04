# Watchlists Design Spec

**Issue:** #5
**Date:** 2026-04-04
**Status:** Approved

## Overview

Evolve the "recently viewed" feature into proper named watchlists with live quotes, supporting both equity tickers and individual options contracts. This replaces the `RecentlyViewed` widget with a `WatchlistPanel` and adds persistence, management UI, and keybindings.

## Data Models & Persistence

### Data Structures

New file: `src/tenortui/watchlists.py`

```python
@dataclass
class WatchlistItem:
    type: str  # "equity" or "option"
    symbol: str
    strike: float | None = None
    option_type: str | None = None  # "call" or "put"
    expiration: str | None = None  # "2026-04-17"

@dataclass
class Watchlist:
    name: str
    items: list[WatchlistItem]

@dataclass
class WatchlistData:
    watchlists: list[Watchlist]
    active_index: int = 0
```

### Persistence Format

File: `~/.config/tenor/watchlists.json`

```json
{
  "watchlists": [
    {
      "name": "Default",
      "items": [
        {"type": "equity", "symbol": "AAPL"},
        {"type": "option", "symbol": "AAPL", "strike": 180, "option_type": "put", "expiration": "2026-04-17"}
      ]
    }
  ],
  "active_index": 0
}
```

### Module Functions

- `load_watchlists(path) -> WatchlistData` — loads from JSON, returns empty default if missing
- `save_watchlists(data: WatchlistData, path) -> None` — writes JSON
- `migrate_from_history(history_path, watchlists_path) -> WatchlistData` — one-time migration: reads `history.json`, creates a "Default" watchlist with those symbols as equity items, saves to `watchlists.json`. Only runs if `watchlists.json` doesn't exist and `history.json` does.
- `add_item(data, watchlist_index, item) -> WatchlistData` — adds item, deduplicates
- `remove_item(data, watchlist_index, item_index) -> WatchlistData` — removes item
- `create_watchlist(data, name) -> WatchlistData` — adds new empty watchlist
- `rename_watchlist(data, index, name) -> WatchlistData` — renames watchlist
- `delete_watchlist(data, index) -> WatchlistData` — removes watchlist (prevents deleting last one)

## WatchlistPanel Widget

New file: `src/tenortui/widgets/watchlist_panel.py`

Replaces `RecentlyViewed`. Mounted in the same position in the widget hierarchy.

### Layout

```
WatchlistPanel
├── Horizontal (tab bar)
│   ├── Button("Default", classes="wl-tab active")
│   ├── Button("Tech", classes="wl-tab")
│   └── ...
├── ListView (watchlist items)
│   ├── ListItem: "AAPL  $213.25  +1.42 (+0.67%)"
│   ├── ListItem: "  180P 04/17  0.45/0.50  mid 0.48  DTE: 13"
│   ├── ListItem: "MSFT  $415.10  -2.30 (-0.55%)"
│   └── ...
└── Static (empty state message)
```

### Display Format

- **Equity row:** `AAPL  $213.25  +1.42 (+0.67%)  54.2M vol`
- **Contract row (indented):** `  180P 04/17  0.45/0.50  mid 0.48  DTE: 13`
- **Expiration warning:** Contracts with DTE <= 7 get a warning indicator (yellow highlight or warning prefix)

### Grouping Logic

Items are displayed grouped by underlying symbol:
- Equity items render as header rows with price/change
- Option contracts for the same underlying render indented below
- If an underlying has only contracts (no equity entry), the symbol still appears as a group header without quote data

### Messages

- `WatchlistPanel.TickerSelected(symbol: str)` — when user selects an equity row
- `WatchlistPanel.WatchlistChanged(index: int)` — when user switches watchlist tabs

### Key Methods

- `update_equity_quotes(quotes: list[Quote])` — refreshes equity price data
- `update_contract_quotes(contracts: dict[tuple[str, str], list[OptionContract]])` — refreshes contract data, keyed by (symbol, expiration)
- `set_watchlists(data: WatchlistData)` — rebuilds tab bar and item list
- `remove_selected_item() -> WatchlistItem | None` — removes currently highlighted item

## Watchlist Picker Modal

New file: `src/tenortui/widgets/watchlist_picker.py`

### WatchlistPicker (on `w` press)

Modal screen to select which watchlist to add an item to. Follows existing `SettingsScreen` pattern.

```
┌─────────────────────────┐
│  Add to Watchlist        │
│                          │
│  > Default               │
│    Tech                  │
│    CSP Candidates        │
│                          │
│  [n] New watchlist...    │
│  [Esc] Cancel            │
└─────────────────────────┘
```

- `ListView` of watchlist names
- `n` to create new watchlist inline (Input prompt for name)
- Vim navigation (`j`/`k`)
- Returns selected watchlist index via callback

### WatchlistManager (on `W` press)

Modal screen for watchlist CRUD operations.

```
┌─────────────────────────┐
│  Manage Watchlists       │
│                          │
│  > Default (5 items)     │
│    Tech (3 items)        │
│    CSP Candidates (0)    │
│                          │
│  [n] New  [r] Rename     │
│  [d] Delete  [Esc] Close │
└─────────────────────────┘
```

- `n` — create new watchlist
- `r` — rename selected (Input with current name pre-filled)
- `d` — delete selected (with confirmation, can't delete last)
- `Esc` — close and return updated `WatchlistData`

## App Integration

### Initialization (app.py)

On mount:
1. Call `migrate_from_history()` then `load_watchlists()`
2. Store `_watchlist_data: WatchlistData` as app state
3. Mount `WatchlistPanel` in place of `RecentlyViewed`
4. Kick off quote fetch worker for active watchlist

### Keybindings

- `w` — context-sensitive:
  - Focus in `ChainTable`: add highlighted contract to watchlist (shows `WatchlistPicker`)
  - Focus elsewhere with ticker loaded: add current ticker as equity (shows `WatchlistPicker`)
  - No ticker loaded and not in chain table: no-op
- `W` — open `WatchlistManager` modal
- `d` — if focus in `WatchlistPanel`: remove highlighted item from current watchlist

### Quote Refresh

New worker `_fetch_watchlist_quotes()` (group "watchlist-quotes"):
- Collects unique equity symbols from active watchlist -> `batch_quotes()`
- Groups option items by (symbol, expiration) -> `get_chain()` per group, extracts matching contracts
- Passes results to `WatchlistPanel.update_equity_quotes()` and `update_contract_quotes()`

Triggered on: app mount, watchlist tab switch, item added/removed, auto-refresh cycle.

The existing auto-refresh system is extended: `_on_auto_refresh()` also refreshes watchlist quotes.

### Message Handling

- `on_watchlist_panel_ticker_selected()` — delegates to `_load_ticker()`
- `on_watchlist_panel_watchlist_changed()` — triggers `_fetch_watchlist_quotes()`

### Replacing History Calls

The `add_to_history()` call in `_load_ticker()` is replaced with adding the ticker to the active watchlist via `add_item()`.

## Migration & Backwards Compatibility

On app startup:
1. Check if `~/.config/tenor/watchlists.json` exists
2. If not, check if `~/.config/tenor/history.json` exists
3. If history exists, create "Default" watchlist with history symbols as equity items
4. Save to `watchlists.json`
5. Leave `history.json` in place (no destructive action)

After migration, `history.json` is no longer read or written. The `history.py` module remains in the codebase.

## Testing Strategy

### Unit Tests (`test_watchlists.py`)

- `load_watchlists` — empty file, valid file, malformed JSON
- `save_watchlists` — round-trip serialization
- `migrate_from_history` — with history, without history, already migrated (no-op)
- `add_item` — equity, option, deduplication
- `remove_item` — valid index, edge cases
- `create_watchlist`, `rename_watchlist`, `delete_watchlist` — including preventing deletion of last watchlist

### Widget Tests (`test_watchlist_panel.py`)

- Rendering equity items with quotes
- Rendering grouped contracts with DTE and expiration warning
- Tab switching between watchlists
- Item selection posting `TickerSelected` message
- `remove_selected_item()` behavior

### Integration Tests (additions to existing test files)

- `w` keybinding opens picker from chain table, adds contract
- `w` keybinding adds current ticker as equity
- `W` opens manager with create/rename/delete operations
- `d` removes item from watchlist panel
- Migration from history on first launch
- Watchlist quote refresh triggers

### Existing Tests

All existing tests continue to pass. `FakeProvider` in conftest needs no changes since we reuse `get_chain()`.
