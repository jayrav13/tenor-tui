# Enhanced Chain Table — Design Spec

**Issue:** #14
**Date:** 2026-04-04

## Overview

Enhance the options chain table with sorting, filtering, visual highlights, and improved Greeks display.

## Architecture

Extract filtering/sorting logic into a new `src/tenortui/chain_filters.py` module with pure functions for easy unit testing. `ChainTable` stays responsible for rendering and visual highlights. Command palette gets new `:filter` commands.

## 1. Sorting

- Track `_sort_column: str | None` and `_sort_reverse: bool` on `ChainTable`
- Column header click or key press toggles sort: ascending -> descending -> none
- Sort indicator arrow (▲/▼) appended to the active column label
- Contracts sorted after filtering, before rendering; ATM divider repositioned after sort
- When a `DataTable` is focused, `Enter` on a column header triggers sort

## 2. Filtering

Filters applied via command palette (`:filter` commands), fitting the existing `:` command pattern:

- `:filter volume > 0` — hide zero-volume strikes
- `:filter itm` / `:filter otm` — show only ITM or OTM
- `:filter delta 0.2 0.8` — min/max delta range
- `:filter oi > 100` — min OI threshold
- `:filter clear` — reset all filters

Filters stored as a `ChainFilters` dataclass on `ChainTable`. Applied as pure functions in `chain_filters.py` before sorting. Active filter count shown in section labels.

## 3. Visual Highlights

- **IV color-coding:** Compute percentile rank of each contract's IV within the chain. Map to gradient: cool (blue/cyan) for low IV -> warm (red/yellow) for high IV. Applied as Rich `Text` style on the IV cell.
- **High-volume/OI highlighting:** Contracts with volume or OI > 2x the chain median get bold styling on those cells.
- **Earnings warning:** If `Quote.earnings_date` exists and the chain expiration crosses it, show a warning indicator in the section label ("CALLS -- Earnings: Apr 24").

## 4. Greeks Display Improvements

- Color-code delta on a gradient: deep ITM (delta near +/-1.0) = bright green, ATM (+/-0.5) = yellow, deep OTM (near 0) = red. Applied as Rich `Text` style.

## Files Changed

| File | Change |
|------|--------|
| `src/tenortui/chain_filters.py` | **New** — `filter_contracts()`, `sort_contracts()`, `ChainFilters` dataclass |
| `src/tenortui/widgets/chain_table.py` | Add sort state, filter state, visual highlighting in `_populate_table`, earnings warning |
| `src/tenortui/widgets/command_palette.py` | Parse `:filter` commands, post message to app |
| `src/tenortui/app.py` | Handle filter commands, pass `earnings_date` to `ChainTable` |
| `tests/test_chain_filters.py` | **New** — unit tests for filtering and sorting pure functions |
| `tests/test_chain_table_enhanced.py` | **New** — widget tests for visual highlights, sort indicators, filter integration |

## Testing Strategy

- Pure function tests for all filter/sort logic (fast, no Textual app needed)
- Widget tests for visual rendering (Rich Text styles, column headers)
- Integration test for command palette -> filter -> display pipeline
