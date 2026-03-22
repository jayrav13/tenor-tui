# Stock Fundamentals Panel Design

**Issue:** #11 (compact mode only)
**Date:** 2026-03-21
**Status:** Approved

## Overview

Add a compact fundamentals bar below the ticker bar showing key stock metrics. Visible only after a ticker is loaded. Data sourced from the existing `yfinance` `Ticker.info` call with no additional API hit.

## Data Layer

Extend the `Quote` dataclass in `models.py` with optional fundamental fields:

```python
pe_ratio: float | None = None
eps: float | None = None
dividend_yield: float | None = None
earnings_date: str | None = None
moving_avg_50d: float | None = None
moving_avg_200d: float | None = None
```

All default to `None`. The Yahoo provider populates them from `Ticker.info`:

| Field | `Ticker.info` key | Notes |
|---|---|---|
| `pe_ratio` | `trailingPE` | `_safe_float_or_none`; may be `NaN` |
| `eps` | `trailingEps` | `_safe_float_or_none`; may be `NaN`. Key is `trailingEps` not `epsTrailingTwelveMonths` (both exist, same value) |
| `dividend_yield` | `dividendYield` | `_safe_float_or_none`; **already in percentage form** (e.g., `0.42` means 0.42%, not 42%). Display directly with `%` suffix, no multiplication needed |
| `earnings_date` | `earningsTimestamp` | **Singular** Unix timestamp (int); convert to `"Mon DD"` format (e.g., "Feb 13") at provider level using `datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%b %d")`; `None` if key missing |
| `moving_avg_50d` | `fiftyDayAverage` | `_safe_float_or_none` |
| `moving_avg_200d` | `twoHundredDayAverage` | `_safe_float_or_none` |

**Verified against live `yfinance` AAPL response on 2026-03-21.**

**NaN handling:** `_safe_float` already converts `NaN` to `0.0`, but for fundamental fields `NaN` should map to `None` (absence of data, not zero). Add a `_safe_float_or_none` helper that returns `None` for `NaN`/missing values instead of `0.0`.

**Tradier provider** leaves all fields as `None`.

**`batch_quotes()` in `yahoo.py`** also constructs `Quote` objects for the Recently Viewed panel. Since all new fields have `= None` defaults, `batch_quotes()` continues to work without changes. Fundamentals are intentionally omitted from batch quotes — they're only relevant when viewing a single ticker, and adding them to batch quotes would slow down the Recently Viewed fetch for no UI benefit.

**`FakeProvider` / `conftest.py`:** Existing `sample_quote` fixture is unchanged (new fields default to `None`). Add a new `sample_quote_with_fundamentals` fixture for testing the fundamentals bar with populated data.

## Widget: FundamentalsBar

New widget at `src/tenortui/widgets/fundamentals_bar.py`.

### Display Format

Single horizontal row with pipe-separated metrics:

```
P/E: 28.5 | EPS: $6.42 | Div: 0.42% | Earnings: Feb 13 | 50d: $261.13 | 200d: $246.82
```

`dividend_yield` is already in percentage form from yfinance — display directly with `%` suffix (no multiplication).

### Behavior

- Omits any individual metric where the value is `None` (e.g., no dividend yield for a non-dividend stock shows: `P/E: 28.5 | EPS: $6.42 | Earnings: Feb 13 | ...`)
- If ALL fundamental fields are `None`, the widget stays hidden (no empty bar)
- Hidden on app launch (`display = False` set in widget `__init__`), shown after a ticker with fundamentals loads
- No keybinding added in this phase — the `f` toggle for an expanded view is deferred

### Styling

- Docked below TickerBar via `dock: top` in `DEFAULT_CSS` (Textual stacks docked-top widgets in yield order, so TickerBar at height 3 + FundamentalsBar at height 1 = 4 lines from top)
- `height: 1` (single line)
- Muted text color (`$text-muted`) to avoid competing with the quote display
- Background matches app surface

### API

- `show_fundamentals(quote: Quote)` — updates display from a Quote, shows widget if any fundamentals present, hides if all `None`
- `hide()` — sets `display = False`

## App Integration

### compose()

Add `FundamentalsBar` between `TickerBar` and `#main-content` in `TenorTUI.compose()`:

```python
yield TickerBar()
yield FundamentalsBar()  # new
with Vertical(id="main-content"):
    ...
```

### _load_ticker()

- **At the start** of `_load_ticker()`: call `self.query_one(FundamentalsBar).hide()` to clear stale data while loading
- **After** `ticker_bar.show_quote(quote)`: call `self.query_one(FundamentalsBar).show_fundamentals(quote)`
- **On error paths** (`SymbolNotFoundError`, `ProviderError`): fundamentals bar is already hidden from the start-of-method call, so no additional action needed

### Yahoo Provider Changes

In `YahooProvider.get_quote()`, extract additional fields from the already-fetched `info` dict. Use `_safe_float_or_none` for numeric fields (returns `None` for `NaN`/missing, not `0.0`). Convert `earningsTimestamp` (singular Unix epoch) to a formatted UTC date string.

## Testing

### Model Tests (test_models.py)

- `test_quote_fundamentals_default_none` — all new fields default to `None`
- `test_quote_with_fundamentals` — fields populated correctly

### Widget Tests (test_widgets_coverage.py)

- `test_fundamentals_bar_displays_metrics` — shows formatted metrics for a quote with fundamentals
- `test_fundamentals_bar_omits_none_fields` — metrics with `None` values are omitted
- `test_fundamentals_bar_hidden_when_all_none` — widget stays hidden when all fundamentals are `None`

### Provider Tests (test_yahoo_provider.py)

- `test_earnings_date_conversion` — verify `earningsTimestamp` is converted to formatted date string

### Fixtures (conftest.py)

- Add `sample_quote_with_fundamentals` fixture with all fundamental fields populated

## Scope Exclusions

- No expanded panel (toggled with `f`) — deferred to a follow-up issue
- No moving average comparison text (e.g., "2.7% above 50-day") — deferred
- No 52-week high/low, sector, or beta — can be added later
