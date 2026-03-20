# Recently Viewed — Design Spec

## Overview

Show a navigable list of recently viewed tickers on the main page at app launch. The list displays live-fetched company names and prices. Selecting a ticker loads its options chain.

## Data Layer

### History file: `~/.config/tenor/history.json`

- JSON array of ticker symbols, most recent first, max 10, deduped
- Example: `["AAPL", "MSFT", "TSLA"]`
- Ticker symbol is the only persisted data; everything else is fetched live

### Config migration: `~/.config/tenor/config.yaml`

- Replaces `~/.tenorrc` (same YAML format, new path)
- Update `config.py` default path, README, CLI help text
- Check `~/.tenorrc` as fallback for backward compatibility

## Batch Quote Fetch

- New function that takes a list of symbols and returns quotes using `yf.download()` + `yf.Tickers()` in a single API call
- Called on app mount when history is non-empty
- Runs via `asyncio.to_thread` to keep UI responsive
- Always uses Yahoo Finance regardless of configured provider (Yahoo is free, no auth needed)

## Widget: `RecentlyViewed`

- New file: `src/tenortui/widgets/recently_viewed.py`
- Displayed in `#main-content` area on launch, replacing the "Search for a ticker" placeholder
- Each row shows: `AAPL  Apple Inc.  $213.25`
- Arrow keys to navigate rows, Enter to select
- Selection posts `TickerBar.TickerSubmitted` message to reuse existing ticker load flow
- Shows loading state while batch quote fetch is in progress
- Hidden once a ticker is loaded

## New Module: `history.py`

- `src/tenortui/history.py`
- `load_history(path) -> list[str]` — reads history file, returns symbol list
- `save_history(symbols: list[str], path)` — writes symbol list to file, creates `~/.config/tenor/` if needed
- `add_to_history(symbol: str, path) -> list[str]` — adds symbol to front, dedupes, caps at 10, persists

## App Flow Changes

### On mount
1. Load history from `~/.config/tenor/history.json`
2. If non-empty: mount `RecentlyViewed` widget, kick off batch quote fetch in background thread
3. If empty: show current empty state ("Search for a ticker to view options chain")

### On ticker submit (existing flow, modified)
1. After successful quote + chain load, call `add_to_history(symbol)`
2. Hide `RecentlyViewed` widget if visible

### Widget lifecycle
- `RecentlyViewed` is mounted at compose time inside `#main-content`
- Hidden/removed when a chain is loaded
- Not re-shown in this scope (no "home" action yet)

## Files Changed

| File | Change |
|------|--------|
| `src/tenortui/config.py` | Default path to `~/.config/tenor/config.yaml`, fallback to `~/.tenorrc` |
| `src/tenortui/history.py` | New — history read/write utilities |
| `src/tenortui/widgets/recently_viewed.py` | New — selectable recently viewed list |
| `src/tenortui/app.py` | Mount `RecentlyViewed`, write history on load, hide widget on chain display |
| `src/tenortui/providers/yahoo.py` | New batch quote function |
| `README.md` | Update config path references |
| `CLAUDE.md` | Update config path references |
