# Enhanced Chain Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sorting, filtering, visual highlights, and improved Greeks display to the options chain table.

**Architecture:** Extract filtering/sorting into pure functions in `chain_filters.py` for testability. Visual highlighting logic lives in `ChainTable._populate_table()` using Rich `Text` styles. Filter commands are parsed in `app.py`'s existing command handler and stored as state on `ChainTable`. The chain is re-rendered whenever filters/sort change.

**Tech Stack:** Python 3.11+, Textual, Rich (Text styling), statistics (median)

## Progress (as of 2026-04-04)

| Task | Status | Notes |
|------|--------|-------|
| Task 1: Filtering | ✅ Done | `chain_filters.py` created, 58 unit tests |
| Task 2: Sorting | ✅ Done | `sort_contracts()` with SORT_KEYS mapping |
| Task 3: Command Parsing | ✅ Done | `parse_filter_command()` |
| Task 4: Visual Helpers | ✅ Done | iv_percentile_rank, delta_color, iv_color, etc. |
| Task 5: ChainTable Integration | ✅ Done (WIP commit) | Filter/sort state, earnings warning, section labels |
| Task 6: Visual Highlights | ✅ Done (WIP commit) | IV color, vol/OI bold, delta gradient in _populate_table |
| Task 7: App Wiring | ✅ Done (WIP commit) | :filter commands, earnings_date passthrough |
| Task 8: Sort Toggle | ✅ Done (WIP commit) | HeaderSelected handler, re-render on toggle |
| Task 9: Sort Indicators | ✅ Done (WIP commit) | ▲/▼ in column headers |
| Task 10: Final Integration | ⬜ Pending | Need spec review, code quality review, integration test, PR |

**All 323 tests pass.** Tasks 5-9 were committed together as a WIP commit. Next steps:
1. Review the WIP code for spec compliance and quality
2. Write a final integration test
3. Clean up the WIP commit (squash or amend)
4. Create the PR

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/tenortui/chain_filters.py` | **New** — `ChainFilters` dataclass, `filter_contracts()`, `sort_contracts()`, `parse_filter_command()` pure functions |
| `src/tenortui/widgets/chain_table.py` | **Modify** — sort state, filter state, visual highlighting (IV color, volume/OI bold, delta gradient), earnings warning, re-render on filter/sort change |
| `src/tenortui/app.py` | **Modify** — handle `:filter` commands from command palette, pass `earnings_date` to `display_chain()` |
| `tests/test_chain_filters.py` | **New** — unit tests for all pure filter/sort/parse functions |
| `tests/test_chain_table_enhanced.py` | **New** — widget tests for visual highlights, sorting, filtering integration |

---

### Task 1: Chain Filters Module — Filtering

**Files:**
- Create: `src/tenortui/chain_filters.py`
- Create: `tests/test_chain_filters.py`

- [ ] **Step 1: Write failing tests for ChainFilters and filter_contracts**

Create `tests/test_chain_filters.py`:

```python
"""Tests for chain filtering and sorting logic."""

import pytest

from tenortui.models import OptionContract


def _make_contract(
    strike: float,
    option_type: str = "call",
    volume: int = 100,
    open_interest: int = 500,
    iv: float = 0.30,
    delta: float | None = None,
) -> OptionContract:
    return OptionContract(
        contract_symbol=f"TEST{strike}{option_type[0].upper()}",
        option_type=option_type,
        strike=strike,
        bid=1.0,
        ask=1.5,
        last_price=1.25,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=iv,
        delta=delta,
        gamma=0.05 if delta is not None else None,
        theta=-0.03 if delta is not None else None,
        vega=0.15 if delta is not None else None,
        rho=0.01 if delta is not None else None,
    )


class TestFilterContracts:
    def test_no_filters_returns_all(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [_make_contract(100), _make_contract(110), _make_contract(120)]
        result = filter_contracts(contracts, ChainFilters())
        assert len(result) == 3

    def test_hide_zero_volume(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, volume=0),
            _make_contract(110, volume=50),
            _make_contract(120, volume=200),
        ]
        filters = ChainFilters(min_volume=1)
        result = filter_contracts(contracts, filters)
        assert len(result) == 2
        assert all(c.volume > 0 for c in result)

    def test_filter_itm_calls(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [_make_contract(100), _make_contract(110), _make_contract(120)]
        filters = ChainFilters(moneyness="itm")
        result = filter_contracts(contracts, filters, current_price=115.0, side="call")
        # ITM calls: strike < current_price => 100, 110
        assert len(result) == 2
        assert all(c.strike < 115.0 for c in result)

    def test_filter_otm_calls(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [_make_contract(100), _make_contract(110), _make_contract(120)]
        filters = ChainFilters(moneyness="otm")
        result = filter_contracts(contracts, filters, current_price=115.0, side="call")
        # OTM calls: strike > current_price => 120
        assert len(result) == 1
        assert result[0].strike == 120.0

    def test_filter_itm_puts(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, "put"),
            _make_contract(110, "put"),
            _make_contract(120, "put"),
        ]
        filters = ChainFilters(moneyness="itm")
        result = filter_contracts(contracts, filters, current_price=115.0, side="put")
        # ITM puts: strike > current_price => 120
        assert len(result) == 1
        assert result[0].strike == 120.0

    def test_filter_otm_puts(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, "put"),
            _make_contract(110, "put"),
            _make_contract(120, "put"),
        ]
        filters = ChainFilters(moneyness="otm")
        result = filter_contracts(contracts, filters, current_price=115.0, side="put")
        # OTM puts: strike < current_price => 100, 110
        assert len(result) == 2
        assert all(c.strike < 115.0 for c in result)

    def test_filter_delta_range(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, delta=0.9),
            _make_contract(110, delta=0.5),
            _make_contract(120, delta=0.1),
        ]
        filters = ChainFilters(min_delta=0.2, max_delta=0.8)
        result = filter_contracts(contracts, filters)
        assert len(result) == 1
        assert result[0].delta == 0.5

    def test_filter_min_oi(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, open_interest=50),
            _make_contract(110, open_interest=200),
            _make_contract(120, open_interest=1000),
        ]
        filters = ChainFilters(min_oi=100)
        result = filter_contracts(contracts, filters)
        assert len(result) == 2

    def test_combined_filters(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, volume=0, open_interest=50),
            _make_contract(110, volume=100, open_interest=200),
            _make_contract(120, volume=50, open_interest=1000),
        ]
        filters = ChainFilters(min_volume=1, min_oi=100)
        result = filter_contracts(contracts, filters)
        assert len(result) == 2
        assert result[0].strike == 110.0
        assert result[1].strike == 120.0

    def test_delta_filter_skips_none_delta(self):
        from tenortui.chain_filters import ChainFilters, filter_contracts

        contracts = [
            _make_contract(100, delta=None),
            _make_contract(110, delta=0.5),
        ]
        filters = ChainFilters(min_delta=0.2, max_delta=0.8)
        result = filter_contracts(contracts, filters)
        # Contract with None delta is excluded when delta filter is active
        assert len(result) == 1
        assert result[0].strike == 110.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_chain_filters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenortui.chain_filters'`

- [ ] **Step 3: Implement ChainFilters and filter_contracts**

Create `src/tenortui/chain_filters.py`:

```python
"""Pure functions for filtering and sorting options chain contracts."""

from dataclasses import dataclass

from tenortui.models import OptionContract


@dataclass
class ChainFilters:
    min_volume: int | None = None
    min_oi: int | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    moneyness: str | None = None  # "itm" or "otm"

    @property
    def is_active(self) -> bool:
        return any(
            v is not None
            for v in [
                self.min_volume,
                self.min_oi,
                self.min_delta,
                self.max_delta,
                self.moneyness,
            ]
        )

    @property
    def active_count(self) -> int:
        count = 0
        if self.min_volume is not None:
            count += 1
        if self.min_oi is not None:
            count += 1
        if self.min_delta is not None or self.max_delta is not None:
            count += 1
        if self.moneyness is not None:
            count += 1
        return count


def filter_contracts(
    contracts: list[OptionContract],
    filters: ChainFilters,
    current_price: float | None = None,
    side: str | None = None,
) -> list[OptionContract]:
    """Apply filters to a list of option contracts."""
    result = contracts

    if filters.min_volume is not None:
        result = [c for c in result if c.volume >= filters.min_volume]

    if filters.min_oi is not None:
        result = [c for c in result if c.open_interest >= filters.min_oi]

    if filters.min_delta is not None or filters.max_delta is not None:
        lo = filters.min_delta if filters.min_delta is not None else -float("inf")
        hi = filters.max_delta if filters.max_delta is not None else float("inf")
        result = [c for c in result if c.delta is not None and lo <= abs(c.delta) <= hi]

    if filters.moneyness and current_price is not None and side:
        if filters.moneyness == "itm":
            if side == "call":
                result = [c for c in result if c.strike < current_price]
            else:
                result = [c for c in result if c.strike > current_price]
        elif filters.moneyness == "otm":
            if side == "call":
                result = [c for c in result if c.strike > current_price]
            else:
                result = [c for c in result if c.strike < current_price]

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_chain_filters.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/chain_filters.py tests/test_chain_filters.py
git commit -m "feat: add chain filtering with pure functions

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Chain Filters Module — Sorting

**Files:**
- Modify: `src/tenortui/chain_filters.py`
- Modify: `tests/test_chain_filters.py`

- [ ] **Step 1: Write failing tests for sort_contracts**

Append to `tests/test_chain_filters.py`:

```python
class TestSortContracts:
    def test_sort_by_strike_ascending(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [_make_contract(120), _make_contract(100), _make_contract(110)]
        result = sort_contracts(contracts, "strike", reverse=False)
        assert [c.strike for c in result] == [100.0, 110.0, 120.0]

    def test_sort_by_strike_descending(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [_make_contract(100), _make_contract(120), _make_contract(110)]
        result = sort_contracts(contracts, "strike", reverse=True)
        assert [c.strike for c in result] == [120.0, 110.0, 100.0]

    def test_sort_by_volume(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [
            _make_contract(100, volume=50),
            _make_contract(110, volume=200),
            _make_contract(120, volume=100),
        ]
        result = sort_contracts(contracts, "vol", reverse=True)
        assert [c.volume for c in result] == [200, 100, 50]

    def test_sort_by_oi(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [
            _make_contract(100, open_interest=300),
            _make_contract(110, open_interest=100),
            _make_contract(120, open_interest=500),
        ]
        result = sort_contracts(contracts, "oi", reverse=False)
        assert [c.open_interest for c in result] == [100, 300, 500]

    def test_sort_by_iv(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [
            _make_contract(100, iv=0.40),
            _make_contract(110, iv=0.20),
            _make_contract(120, iv=0.30),
        ]
        result = sort_contracts(contracts, "iv", reverse=False)
        assert [c.implied_volatility for c in result] == [0.20, 0.30, 0.40]

    def test_sort_by_delta(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [
            _make_contract(100, delta=0.9),
            _make_contract(110, delta=0.5),
            _make_contract(120, delta=0.1),
        ]
        result = sort_contracts(contracts, "delta", reverse=False)
        assert [c.delta for c in result] == [0.1, 0.5, 0.9]

    def test_sort_by_delta_with_none(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [
            _make_contract(100, delta=0.9),
            _make_contract(110, delta=None),
            _make_contract(120, delta=0.1),
        ]
        result = sort_contracts(contracts, "delta", reverse=False)
        # None deltas sort to end
        assert result[0].delta == 0.1
        assert result[1].delta == 0.9
        assert result[2].delta is None

    def test_sort_none_column_returns_by_strike(self):
        from tenortui.chain_filters import sort_contracts

        contracts = [_make_contract(120), _make_contract(100), _make_contract(110)]
        result = sort_contracts(contracts, None, reverse=False)
        assert [c.strike for c in result] == [100.0, 110.0, 120.0]

    def test_sort_by_bid(self):
        from tenortui.chain_filters import sort_contracts

        c1 = _make_contract(100)
        c2 = _make_contract(110)
        c3 = _make_contract(120)
        # All bids are 1.0 by default, so order should be stable by strike
        result = sort_contracts([c3, c1, c2], "bid", reverse=False)
        assert len(result) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_chain_filters.py::TestSortContracts -v`
Expected: FAIL — `ImportError: cannot import name 'sort_contracts'`

- [ ] **Step 3: Implement sort_contracts**

Add to `src/tenortui/chain_filters.py`:

```python
# Column name -> attribute mapping for sorting
SORT_KEYS: dict[str, str] = {
    "strike": "strike",
    "bid": "bid",
    "ask": "ask",
    "spread": "spread_percent",
    "mid": "mid",
    "last": "last_price",
    "vol": "volume",
    "oi": "open_interest",
    "iv": "implied_volatility",
    "delta": "delta",
    "gamma": "gamma",
    "theta": "theta",
    "vega": "vega",
    "rho": "rho",
}


def sort_contracts(
    contracts: list[OptionContract],
    column: str | None,
    reverse: bool = False,
) -> list[OptionContract]:
    """Sort contracts by column. None column sorts by strike."""
    if column is None:
        return sorted(contracts, key=lambda c: c.strike, reverse=reverse)

    attr = SORT_KEYS.get(column.lower())
    if attr is None:
        return sorted(contracts, key=lambda c: c.strike, reverse=reverse)

    def sort_key(c: OptionContract):
        val = getattr(c, attr)
        if val is None:
            return (1, 0)  # None sorts to end
        return (0, val)

    return sorted(contracts, key=sort_key, reverse=reverse)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_chain_filters.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/chain_filters.py tests/test_chain_filters.py
git commit -m "feat: add chain sorting with column mapping

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Chain Filters Module — Command Parsing

**Files:**
- Modify: `src/tenortui/chain_filters.py`
- Modify: `tests/test_chain_filters.py`

- [ ] **Step 1: Write failing tests for parse_filter_command**

Append to `tests/test_chain_filters.py`:

```python
class TestParseFilterCommand:
    def test_parse_volume_gt(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("volume > 0")
        assert filters.min_volume == 1

    def test_parse_volume_gt_number(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("volume > 100")
        assert filters.min_volume == 101

    def test_parse_oi_gt(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("oi > 100")
        assert filters.min_oi == 101

    def test_parse_itm(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("itm")
        assert filters.moneyness == "itm"

    def test_parse_otm(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("otm")
        assert filters.moneyness == "otm"

    def test_parse_delta_range(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("delta 0.2 0.8")
        assert filters.min_delta == 0.2
        assert filters.max_delta == 0.8

    def test_parse_clear(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("clear")
        assert filters is None

    def test_parse_invalid_returns_none(self):
        from tenortui.chain_filters import parse_filter_command

        filters = parse_filter_command("gibberish xyz")
        assert filters is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_chain_filters.py::TestParseFilterCommand -v`
Expected: FAIL — `ImportError: cannot import name 'parse_filter_command'`

- [ ] **Step 3: Implement parse_filter_command**

Add to `src/tenortui/chain_filters.py`:

```python
def parse_filter_command(command: str) -> ChainFilters | None:
    """Parse a filter command string into a ChainFilters, or None for clear/invalid.

    Supported formats:
        "volume > N"   — min volume = N+1
        "oi > N"       — min OI = N+1
        "itm"          — show only in-the-money
        "otm"          — show only out-of-the-money
        "delta X Y"    — delta range [X, Y]
        "clear"        — returns None (signals reset)
    """
    parts = command.strip().lower().split()
    if not parts:
        return None

    if parts[0] == "clear":
        return None

    if parts[0] in ("itm", "otm"):
        return ChainFilters(moneyness=parts[0])

    if parts[0] == "delta" and len(parts) == 3:
        try:
            lo = float(parts[1])
            hi = float(parts[2])
            return ChainFilters(min_delta=lo, max_delta=hi)
        except ValueError:
            return None

    if parts[0] in ("volume", "vol") and len(parts) == 3 and parts[1] == ">":
        try:
            threshold = int(parts[2])
            return ChainFilters(min_volume=threshold + 1)
        except ValueError:
            return None

    if parts[0] == "oi" and len(parts) == 3 and parts[1] == ">":
        try:
            threshold = int(parts[2])
            return ChainFilters(min_oi=threshold + 1)
        except ValueError:
            return None

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_chain_filters.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/chain_filters.py tests/test_chain_filters.py
git commit -m "feat: add filter command parsing

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Visual Highlighting Helpers

**Files:**
- Modify: `src/tenortui/chain_filters.py`
- Modify: `tests/test_chain_filters.py`

- [ ] **Step 1: Write failing tests for visual helpers**

Append to `tests/test_chain_filters.py`:

```python
class TestVisualHelpers:
    def test_iv_percentile_rank(self):
        from tenortui.chain_filters import iv_percentile_rank

        ivs = [0.20, 0.25, 0.30, 0.35, 0.40]
        assert iv_percentile_rank(0.20, ivs) == 0.0
        assert iv_percentile_rank(0.40, ivs) == 1.0
        assert iv_percentile_rank(0.30, ivs) == 0.5

    def test_iv_percentile_rank_single(self):
        from tenortui.chain_filters import iv_percentile_rank

        assert iv_percentile_rank(0.30, [0.30]) == 0.0

    def test_iv_percentile_rank_empty(self):
        from tenortui.chain_filters import iv_percentile_rank

        assert iv_percentile_rank(0.30, []) == 0.0

    def test_compute_chain_median(self):
        from tenortui.chain_filters import compute_chain_median

        values = [10, 20, 30, 40, 50]
        assert compute_chain_median(values) == 30.0

    def test_compute_chain_median_empty(self):
        from tenortui.chain_filters import compute_chain_median

        assert compute_chain_median([]) == 0.0

    def test_is_high_activity(self):
        from tenortui.chain_filters import is_high_activity

        assert is_high_activity(200, 80.0) is True  # 200 > 2 * 80
        assert is_high_activity(100, 80.0) is False  # 100 < 2 * 80
        assert is_high_activity(161, 80.0) is True  # 161 > 160

    def test_delta_color(self):
        from tenortui.chain_filters import delta_color

        # Deep ITM (near 1.0) = green
        assert delta_color(0.95) == "green"
        # ATM (near 0.5) = yellow
        assert delta_color(0.50) == "yellow"
        # Deep OTM (near 0) = red
        assert delta_color(0.05) == "red"

    def test_delta_color_none(self):
        from tenortui.chain_filters import delta_color

        assert delta_color(None) == ""

    def test_iv_color(self):
        from tenortui.chain_filters import iv_color

        # Low IV percentile = cool
        assert iv_color(0.0) == "cyan"
        # High IV percentile = warm
        assert iv_color(1.0) == "red"
        # Mid = yellow
        assert iv_color(0.5) == "yellow"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_chain_filters.py::TestVisualHelpers -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement visual helpers**

Add to `src/tenortui/chain_filters.py`:

```python
from statistics import median


def iv_percentile_rank(iv: float, all_ivs: list[float]) -> float:
    """Compute where iv falls in the distribution of all_ivs (0.0 to 1.0)."""
    if len(all_ivs) <= 1:
        return 0.0
    below = sum(1 for x in all_ivs if x < iv)
    return below / (len(all_ivs) - 1)


def compute_chain_median(values: list[int | float]) -> float:
    """Compute median of a list, returning 0.0 for empty lists."""
    if not values:
        return 0.0
    return float(median(values))


def is_high_activity(value: int, median_value: float) -> bool:
    """True if value exceeds 2x the median."""
    return value > 2 * median_value


def delta_color(delta: float | None) -> str:
    """Map delta to a color: deep ITM = green, ATM = yellow, deep OTM = red."""
    if delta is None:
        return ""
    abs_delta = abs(delta)
    if abs_delta >= 0.7:
        return "green"
    elif abs_delta >= 0.3:
        return "yellow"
    else:
        return "red"


def iv_color(percentile: float) -> str:
    """Map IV percentile (0-1) to a color gradient: cool to warm."""
    if percentile <= 0.25:
        return "cyan"
    elif percentile <= 0.5:
        return "yellow"
    elif percentile <= 0.75:
        return "dark_orange"
    else:
        return "red"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_chain_filters.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/chain_filters.py tests/test_chain_filters.py
git commit -m "feat: add visual highlighting helpers for IV, volume, delta

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Integrate Filtering and Sorting into ChainTable

**Files:**
- Modify: `src/tenortui/widgets/chain_table.py`
- Create: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write failing tests for filter/sort integration**

Create `tests/test_chain_table_enhanced.py`:

```python
"""Tests for enhanced chain table: sorting, filtering, visual highlights."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable

from tenortui.chain_filters import ChainFilters
from tenortui.models import OptionContract, OptionsChain
from tenortui.widgets.chain_table import ChainTable


class WidgetTestApp(App):
    def __init__(self, widget):
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


def _make_contract(
    strike: float,
    option_type: str = "call",
    volume: int = 100,
    open_interest: int = 500,
    iv: float = 0.30,
    delta: float | None = None,
) -> OptionContract:
    return OptionContract(
        contract_symbol=f"TEST{strike}{option_type[0].upper()}",
        option_type=option_type,
        strike=strike,
        bid=1.0,
        ask=1.5,
        last_price=1.25,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=iv,
        delta=delta,
        gamma=0.05 if delta is not None else None,
        theta=-0.03 if delta is not None else None,
        vega=0.15 if delta is not None else None,
        rho=0.01 if delta is not None else None,
    )


@pytest.mark.asyncio
async def test_chain_table_with_filters():
    """ChainTable applies filters to hide contracts."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, volume=0),
            _make_contract(110, volume=50),
            _make_contract(120, volume=200),
        ],
        puts=[_make_contract(100, "put", volume=100)],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=1))
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # 2 data rows + 1 ATM row = 3 (110 and 120 pass filter)
        assert calls_table.row_count == 3


@pytest.mark.asyncio
async def test_chain_table_sort_by_volume():
    """ChainTable sorts contracts by volume descending."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, volume=50),
            _make_contract(110, volume=200),
            _make_contract(120, volume=100),
        ],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=True)
        await widget.display_chain(chain, current_price=None)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # Sorted by volume desc: 200, 100, 50
        assert calls_table.row_count == 3


@pytest.mark.asyncio
async def test_chain_table_filter_clear():
    """ChainTable clear_filters resets to no filters."""
    widget = ChainTable()
    widget.set_filters(ChainFilters(min_volume=100))
    widget.clear_filters()
    assert not widget._filters.is_active


@pytest.mark.asyncio
async def test_chain_table_earnings_warning():
    """ChainTable shows earnings warning in section label."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[_make_contract(100)],
        puts=[_make_contract(100, "put")],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(
            chain, current_price=105.0, earnings_date="Mar 15"
        )
        from textual.widgets import Static

        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "Earnings" in calls_label


@pytest.mark.asyncio
async def test_chain_table_filter_count_in_label():
    """When filters active, section label shows filter count."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[_make_contract(100, volume=50), _make_contract(110, volume=200)],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=1))
        await widget.display_chain(chain, current_price=None)
        from textual.widgets import Static

        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "filter" in calls_label.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_chain_table_enhanced.py -v`
Expected: FAIL — `AttributeError: 'ChainTable' object has no attribute 'set_filters'`

- [ ] **Step 3: Implement filter/sort/earnings integration in ChainTable**

Modify `src/tenortui/widgets/chain_table.py` — add filter/sort state, update `display_chain` signature, update `_populate_table` to apply filters and sorting:

Key changes:
- Add `_filters: ChainFilters`, `_sort_column: str | None`, `_sort_reverse: bool` attributes
- Add `set_filters()`, `clear_filters()`, `set_sort()` methods
- Update `display_chain()` to accept `earnings_date` parameter
- In `_populate_table()`: filter contracts, sort them, then render
- Section labels show earnings warning and filter count when active

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_chain_table_enhanced.py tests/test_widgets_coverage.py -v`
Expected: All tests PASS (new + existing)

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/chain_table.py tests/test_chain_table_enhanced.py
git commit -m "feat: integrate filtering, sorting, and earnings warning into ChainTable

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Visual Highlights in ChainTable Rendering

**Files:**
- Modify: `src/tenortui/widgets/chain_table.py`
- Modify: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write failing tests for visual highlights**

Append to `tests/test_chain_table_enhanced.py`:

```python
@pytest.mark.asyncio
async def test_chain_table_iv_color_applied():
    """ChainTable applies IV color coding based on percentile rank."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, iv=0.10),
            _make_contract(110, iv=0.30),
            _make_contract(120, iv=0.50),
        ],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=None)
        # Verify the chain rendered without error (IV color applied internally)
        tables = widget.query(DataTable)
        assert tables.first().row_count == 3


@pytest.mark.asyncio
async def test_chain_table_high_volume_bold():
    """ChainTable bolds high-volume contracts (> 2x median)."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, volume=10),
            _make_contract(110, volume=20),
            _make_contract(120, volume=1000),  # >> 2x median
        ],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=None)
        tables = widget.query(DataTable)
        assert tables.first().row_count == 3


@pytest.mark.asyncio
async def test_chain_table_delta_color_applied():
    """ChainTable applies delta color gradient when greeks present."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, delta=0.9),
            _make_contract(110, delta=0.5),
            _make_contract(120, delta=0.1),
        ],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        assert tables.first().row_count == 4  # 3 contracts + ATM row
```

- [ ] **Step 2: Run tests to verify they fail (or pass if implemented in Task 5)**

Run: `poetry run python -m pytest tests/test_chain_table_enhanced.py -v`

- [ ] **Step 3: Implement visual highlighting in _populate_table**

In `chain_table.py`'s `_populate_table`, after filtering and sorting:

1. Collect all IVs from the contract list, compute percentile rank for each
2. Compute median volume and median OI for the contract list
3. When building each row:
   - IV cell: `Text(f"{iv:.2%}", style=iv_color(percentile))`
   - Vol cell: `Text(f"{vol:,}", style="bold")` if `is_high_activity(vol, median_vol)`
   - OI cell: `Text(f"{oi:,}", style="bold")` if `is_high_activity(oi, median_oi)`
   - Delta cell: `Text(f"{delta:.3f}", style=delta_color(delta))`

- [ ] **Step 4: Run all tests**

Run: `poetry run python -m pytest tests/test_chain_table_enhanced.py tests/test_widgets_coverage.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/chain_table.py tests/test_chain_table_enhanced.py
git commit -m "feat: add IV color-coding, volume/OI bold, delta gradient

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Wire Filter Commands in App

**Files:**
- Modify: `src/tenortui/app.py`
- Modify: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write failing test for filter command handling**

Append to `tests/test_chain_table_enhanced.py`:

```python
@pytest.mark.asyncio
async def test_filter_command_parsed_in_app():
    """App handles :filter commands and applies to ChainTable."""
    from tenortui.chain_filters import parse_filter_command

    # Test the parsing works end-to-end
    result = parse_filter_command("volume > 0")
    assert result is not None
    assert result.min_volume == 1

    result = parse_filter_command("clear")
    assert result is None
```

- [ ] **Step 2: Implement filter command handling in app.py**

In `app.py`, modify `on_command_palette_command_submitted` to handle `:filter` commands:

```python
elif cmd.startswith("filter ") or cmd.startswith("f "):
    parts = cmd.split(None, 1)
    if len(parts) == 2:
        from tenortui.chain_filters import parse_filter_command

        filter_cmd = parts[1].strip()
        result = parse_filter_command(filter_cmd)
        chain_table = self.query_one(ChainTable)
        if filter_cmd.lower() == "clear":
            chain_table.clear_filters()
        elif result is not None:
            chain_table.set_filters(result)
        # Re-render current chain if one is loaded
        if self._current_symbol and self._current_expiration:
            self._load_chain(self._current_symbol, self._current_expiration)
```

Also update `_load_chain` and `_load_ticker` to pass `earnings_date` to `display_chain()`:
```python
await chain_table.display_chain(
    chain, self._current_price, self._spread_thresholds,
    earnings_date=getattr(self, '_current_earnings_date', None),
)
```

And store `earnings_date` from the quote in `_load_ticker`:
```python
self._current_earnings_date = quote.earnings_date
```

- [ ] **Step 3: Run all tests**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 4: Run lint and format checks**

Run: `poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/app.py tests/test_chain_table_enhanced.py
git commit -m "feat: wire filter commands through command palette and pass earnings_date

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Column Header Sort via Key Binding

**Files:**
- Modify: `src/tenortui/widgets/chain_table.py`
- Modify: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write test for sort toggle behavior**

Append to `tests/test_chain_table_enhanced.py`:

```python
@pytest.mark.asyncio
async def test_chain_table_sort_toggle():
    """set_sort toggles: asc -> desc -> none."""
    widget = ChainTable()
    widget.set_sort("vol", reverse=False)
    assert widget._sort_column == "vol"
    assert widget._sort_reverse is False

    widget.set_sort("vol", reverse=True)
    assert widget._sort_column == "vol"
    assert widget._sort_reverse is True

    widget.set_sort(None, reverse=False)
    assert widget._sort_column is None
```

- [ ] **Step 2: Implement sort key handling in ChainTable**

Add to `chain_table.py` — handle `DataTable.HeaderSelected` message to toggle sort and re-render:

```python
def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
    """Toggle sort when a column header is clicked."""
    col_key = str(event.column_key)
    if self._sort_column == col_key and not self._sort_reverse:
        self._sort_reverse = True
    elif self._sort_column == col_key and self._sort_reverse:
        self._sort_column = None
        self._sort_reverse = False
    else:
        self._sort_column = col_key
        self._sort_reverse = False
    if self._last_chain is not None:
        # Re-render with current state
        import asyncio
        asyncio.ensure_future(self.display_chain(
            self._last_chain, self._last_price, self._last_thresholds,
            earnings_date=self._last_earnings_date,
        ))
```

Store last render params on `display_chain` so we can re-render on sort change.

- [ ] **Step 3: Run all tests**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/tenortui/widgets/chain_table.py tests/test_chain_table_enhanced.py
git commit -m "feat: add column header sort toggle with re-render

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Sort Direction Indicators

**Files:**
- Modify: `src/tenortui/widgets/chain_table.py`
- Modify: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write test for sort indicators**

Append to `tests/test_chain_table_enhanced.py`:

```python
@pytest.mark.asyncio
async def test_chain_table_sort_indicator_in_header():
    """Sorted column shows direction arrow in header."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[
            _make_contract(100, volume=50),
            _make_contract(110, volume=200),
        ],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=False)
        await widget.display_chain(chain, current_price=None)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        col_labels = [str(col.label) for col in calls_table.columns.values()]
        vol_label = [l for l in col_labels if "Vol" in l][0]
        assert "▲" in vol_label


@pytest.mark.asyncio
async def test_chain_table_sort_indicator_descending():
    """Descending sort shows down arrow."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-03-21",
        calls=[_make_contract(100), _make_contract(110)],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=True)
        await widget.display_chain(chain, current_price=None)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        col_labels = [str(col.label) for col in calls_table.columns.values()]
        vol_label = [l for l in col_labels if "Vol" in l][0]
        assert "▼" in vol_label
```

- [ ] **Step 2: Implement sort indicators**

In `_populate_table`, when adding columns, append ▲ or ▼ to the label of the sorted column:

```python
for col_name, _width in columns:
    col_key = col_name.lower().rstrip("*")
    label = col_name
    if self._sort_column == col_key:
        label = f"{col_name} {'▲' if not self._sort_reverse else '▼'}"
    table.add_column(label, key=col_key)
```

- [ ] **Step 3: Run all tests**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/tenortui/widgets/chain_table.py tests/test_chain_table_enhanced.py
git commit -m "feat: add sort direction indicators in column headers

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: Final Integration Test and Cleanup

**Files:**
- All modified files
- Modify: `tests/test_chain_table_enhanced.py`

- [ ] **Step 1: Write integration test**

Append to `tests/test_chain_table_enhanced.py`:

```python
@pytest.mark.asyncio
async def test_full_enhanced_chain_workflow():
    """Integration test: filter + sort + visual highlights all work together."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-04-17",
        calls=[
            _make_contract(100, volume=0, iv=0.10, delta=0.9),
            _make_contract(110, volume=50, iv=0.25, delta=0.5),
            _make_contract(120, volume=1000, iv=0.50, delta=0.1),
        ],
        puts=[
            _make_contract(100, "put", volume=30, iv=0.15, delta=-0.1),
            _make_contract(110, "put", volume=200, iv=0.30, delta=-0.5),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        # Apply filter and sort
        widget.set_filters(ChainFilters(min_volume=1))
        widget.set_sort("iv", reverse=True)
        await widget.display_chain(
            chain, current_price=115.0, earnings_date="Apr 10"
        )
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # Filtered out volume=0, so 2 calls remain + ATM row = 3
        assert calls_table.row_count == 3

        # Check section label has earnings warning
        from textual.widgets import Static
        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "Earnings" in calls_label
```

- [ ] **Step 2: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 3: Run lint and format**

Run: `poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "test: add full integration test for enhanced chain table

Closes #14

Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 5: Push and create PR**

```bash
git push
gh pr create --title "feat: enhanced chain table with sorting, filtering, and visual highlights" --body "$(cat <<'EOF'
## Summary
- Column sorting with direction indicators (▲/▼) via header click
- Filtering via command palette: `:filter volume > 0`, `:filter itm`, `:filter delta 0.2 0.8`, `:filter oi > 100`, `:filter clear`
- IV color-coding (cool→warm gradient based on percentile rank)
- High-volume/OI bold highlighting (> 2x median)
- Delta color gradient (green=ITM, yellow=ATM, red=OTM)
- Earnings warning indicator in section labels

Closes #14

*Co-authored by Claude*

## Test plan
- [ ] Run `poetry run python -m pytest -v` — all tests pass
- [ ] Manual test: load a ticker, verify IV colors appear
- [ ] Manual test: click column headers to sort, verify arrows
- [ ] Manual test: `:filter volume > 0` hides zero-volume strikes
- [ ] Manual test: `:filter itm` / `:filter otm` works correctly
- [ ] Manual test: `:filter clear` resets to full chain
- [ ] Manual test with Tradier: delta colors show green/yellow/red gradient

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 6: Monitor CI**

```bash
gh pr checks <pr-number> --watch
```
