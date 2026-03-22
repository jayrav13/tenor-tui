# Stock Fundamentals Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact fundamentals bar showing P/E, EPS, dividend yield, earnings date, 50d MA, and 200d MA below the ticker bar when a ticker is loaded.

**Architecture:** Extend the `Quote` dataclass with optional fundamental fields populated by the Yahoo provider from the existing `Ticker.info` call. A new `FundamentalsBar` widget renders a single muted-text row, hidden until a ticker loads.

**Tech Stack:** Python 3.11+, Textual, yfinance, pytest, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-21-stock-fundamentals-panel-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/tenortui/models.py` | Modify | Add 6 optional fundamental fields to `Quote` |
| `src/tenortui/providers/yahoo.py` | Modify | Add `_safe_float_or_none` helper, populate fundamental fields in `get_quote()` |
| `src/tenortui/widgets/fundamentals_bar.py` | Create | New widget rendering compact fundamentals row |
| `src/tenortui/app.py` | Modify | Add `FundamentalsBar` to compose, wire into `_load_ticker()` |
| `tests/conftest.py` | Modify | Add `sample_quote_with_fundamentals` fixture |
| `tests/fixtures/yahoo_quote.json` | Modify | Add fundamental fields to fixture |
| `tests/test_models.py` | Modify | Add tests for Quote fundamentals fields |
| `tests/test_yahoo_provider.py` | Modify | Add test for earnings date conversion |
| `tests/test_widgets_coverage.py` | Modify | Add FundamentalsBar widget tests |

---

### Task 1: Extend Quote Model with Fundamental Fields

**Files:**
- Modify: `src/tenortui/models.py:5-12`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for Quote fundamentals**

Add to `tests/test_models.py` inside `class TestQuote`:

```python
def test_quote_fundamentals_default_none(self):
    q = Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=213.25,
        change=1.42,
        change_percent=0.67,
        volume=54_200_000,
        market_cap=3_200_000_000_000,
    )
    assert q.pe_ratio is None
    assert q.eps is None
    assert q.dividend_yield is None
    assert q.earnings_date is None
    assert q.moving_avg_50d is None
    assert q.moving_avg_200d is None

def test_quote_with_fundamentals(self):
    q = Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=213.25,
        change=1.42,
        change_percent=0.67,
        volume=54_200_000,
        market_cap=3_200_000_000_000,
        pe_ratio=28.5,
        eps=6.42,
        dividend_yield=0.42,
        earnings_date="Feb 13",
        moving_avg_50d=261.13,
        moving_avg_200d=246.82,
    )
    assert q.pe_ratio == 28.5
    assert q.eps == 6.42
    assert q.dividend_yield == 0.42
    assert q.earnings_date == "Feb 13"
    assert q.moving_avg_50d == 261.13
    assert q.moving_avg_200d == 246.82
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_models.py::TestQuote::test_quote_fundamentals_default_none tests/test_models.py::TestQuote::test_quote_with_fundamentals -v`
Expected: FAIL — `Quote` does not have `pe_ratio` etc.

- [ ] **Step 3: Add fundamental fields to Quote**

In `src/tenortui/models.py`, add after `market_cap: float | None` (line 12):

```python
pe_ratio: float | None = None
eps: float | None = None
dividend_yield: float | None = None
earnings_date: str | None = None
moving_avg_50d: float | None = None
moving_avg_200d: float | None = None
```

**Important:** Since `market_cap` has no default but the new fields do, you must also give `market_cap` a default: change line 12 to `market_cap: float | None = None`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_models.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to check nothing broke**

Run: `poetry run python -m pytest -v`
Expected: ALL PASS (existing `sample_quote` fixture uses positional args, so `market_cap` default doesn't break anything since it was already passed explicitly)

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/models.py tests/test_models.py
git commit -m "feat: add fundamental fields to Quote model

Closes #11 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Add `_safe_float_or_none` and Populate Fundamentals in Yahoo Provider

**Files:**
- Modify: `src/tenortui/providers/yahoo.py:1-42`
- Modify: `tests/fixtures/yahoo_quote.json`
- Test: `tests/test_yahoo_provider.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update the yahoo_quote.json fixture with fundamental fields**

Replace `tests/fixtures/yahoo_quote.json` with:

```json
{
  "shortName": "Apple Inc.",
  "regularMarketPrice": 213.25,
  "regularMarketChange": 1.42,
  "regularMarketChangePercent": 0.67,
  "regularMarketVolume": 54200000,
  "marketCap": 3200000000000,
  "trailingPE": 31.35,
  "trailingEps": 7.91,
  "dividendYield": 0.42,
  "earningsTimestamp": 1769720400,
  "fiftyDayAverage": 261.13,
  "twoHundredDayAverage": 246.82
}
```

- [ ] **Step 2: Write failing test for fundamentals in get_quote**

Add to `tests/test_yahoo_provider.py` inside `class TestYahooProviderGetQuote`:

```python
def test_returns_quote_with_fundamentals(self):
    info = _load_fixture("yahoo_quote.json")
    provider = YahooProvider()
    with patch(
        "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
    ):
        quote = provider.get_quote("AAPL")
    assert quote.pe_ratio == 31.35
    assert quote.eps == 7.91
    assert quote.dividend_yield == 0.42
    assert quote.earnings_date is not None  # formatted date string
    assert quote.moving_avg_50d == 261.13
    assert quote.moving_avg_200d == 246.82
```

- [ ] **Step 3: Write failing test for earnings date conversion**

Add to `tests/test_yahoo_provider.py` inside `class TestYahooProviderGetQuote`:

```python
def test_earnings_date_formatted(self):
    info = _load_fixture("yahoo_quote.json")
    provider = YahooProvider()
    with patch(
        "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
    ):
        quote = provider.get_quote("AAPL")
    # earningsTimestamp 1769720400 = Jan 29 2026 UTC
    assert quote.earnings_date == "Jan 29"

def test_quote_without_fundamentals(self):
    info = {
        "shortName": "Test Corp.",
        "regularMarketPrice": 100.0,
        "regularMarketChange": 0.5,
        "regularMarketChangePercent": 0.5,
        "regularMarketVolume": 1000000,
        "marketCap": 500000000,
    }
    provider = YahooProvider()
    with patch(
        "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
    ):
        quote = provider.get_quote("TEST")
    assert quote.pe_ratio is None
    assert quote.eps is None
    assert quote.earnings_date is None

def test_nan_fundamentals_become_none(self):
    info = {
        "shortName": "NaN Corp.",
        "regularMarketPrice": 100.0,
        "regularMarketChange": 0.0,
        "regularMarketChangePercent": 0.0,
        "regularMarketVolume": 1000000,
        "marketCap": 500000000,
        "trailingPE": float("nan"),
        "trailingEps": float("nan"),
        "dividendYield": float("nan"),
        "fiftyDayAverage": float("nan"),
        "twoHundredDayAverage": float("nan"),
    }
    provider = YahooProvider()
    with patch(
        "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
    ):
        quote = provider.get_quote("NAN")
    assert quote.pe_ratio is None
    assert quote.eps is None
    assert quote.dividend_yield is None
    assert quote.moving_avg_50d is None
    assert quote.moving_avg_200d is None

def test_invalid_earnings_timestamp_becomes_none(self):
    info = {
        "shortName": "Bad Earnings Corp.",
        "regularMarketPrice": 100.0,
        "regularMarketChange": 0.0,
        "regularMarketChangePercent": 0.0,
        "regularMarketVolume": 1000000,
        "marketCap": 500000000,
        "earningsTimestamp": "not_a_timestamp",
    }
    provider = YahooProvider()
    with patch(
        "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
    ):
        quote = provider.get_quote("BAD")
    assert quote.earnings_date is None
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_yahoo_provider.py -v`
Expected: FAIL — `get_quote` doesn't populate fundamental fields yet

- [ ] **Step 5: Implement `_safe_float_or_none` and update `get_quote`**

In `src/tenortui/providers/yahoo.py`, add `import datetime` at the top (after `import math`, line 1). Then add after `_safe_float` (after line 18):

```python
def _safe_float_or_none(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _format_earnings_date(timestamp) -> str | None:
    if timestamp is None:
        return None
    try:
        dt = datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc)
        return dt.strftime("%b %d")
    except (ValueError, TypeError, OSError):
        return None
```

Update the `return Quote(...)` in `get_quote()` (lines 34-42) to:

```python
return Quote(
    symbol=symbol.upper(),
    name=info.get("shortName", symbol),
    price=info["regularMarketPrice"],
    change=info.get("regularMarketChange", 0.0),
    change_percent=info.get("regularMarketChangePercent", 0.0),
    volume=info.get("regularMarketVolume", 0),
    market_cap=info.get("marketCap"),
    pe_ratio=_safe_float_or_none(info.get("trailingPE")),
    eps=_safe_float_or_none(info.get("trailingEps")),
    dividend_yield=_safe_float_or_none(info.get("dividendYield")),
    earnings_date=_format_earnings_date(info.get("earningsTimestamp")),
    moving_avg_50d=_safe_float_or_none(info.get("fiftyDayAverage")),
    moving_avg_200d=_safe_float_or_none(info.get("twoHundredDayAverage")),
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_yahoo_provider.py -v`
Expected: ALL PASS

- [ ] **Step 7: Add `sample_quote_with_fundamentals` fixture to conftest.py**

Add to `tests/conftest.py`:

```python
@pytest.fixture
def sample_quote_with_fundamentals():
    return Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=213.25,
        change=1.42,
        change_percent=0.67,
        volume=54_200_000,
        market_cap=3_200_000_000_000,
        pe_ratio=31.35,
        eps=7.91,
        dividend_yield=0.42,
        earnings_date="Feb 13",
        moving_avg_50d=261.13,
        moving_avg_200d=246.82,
    )
```

- [ ] **Step 8: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add src/tenortui/providers/yahoo.py tests/test_yahoo_provider.py tests/fixtures/yahoo_quote.json tests/conftest.py
git commit -m "feat: populate Quote fundamentals from Yahoo provider

Add _safe_float_or_none helper for NaN-to-None conversion.
Extract P/E, EPS, dividend yield, earnings date, and moving
averages from the existing Ticker.info call.

Closes #11 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Create FundamentalsBar Widget

**Files:**
- Create: `src/tenortui/widgets/fundamentals_bar.py`
- Test: `tests/test_widgets_coverage.py`

- [ ] **Step 1: Write failing widget tests**

Add to `tests/test_widgets_coverage.py`. Add import at top:

```python
from tenortui.widgets.fundamentals_bar import FundamentalsBar
```

Add tests before the `# --- TickerBar ---` section:

```python
# --- FundamentalsBar ---


@pytest.mark.asyncio
async def test_fundamentals_bar_displays_metrics(sample_quote_with_fundamentals):
    """FundamentalsBar shows formatted metrics."""
    widget = FundamentalsBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_fundamentals(sample_quote_with_fundamentals)
        assert widget.display is True
        rendered = widget.query_one("#fundamentals-display").render().plain
        assert "P/E: 31.35" in rendered
        assert "EPS: $7.91" in rendered
        assert "Div: 0.42%" in rendered
        assert "Feb 13" in rendered
        assert "50d: $261.13" in rendered
        assert "200d: $246.82" in rendered


@pytest.mark.asyncio
async def test_fundamentals_bar_omits_none_fields():
    """FundamentalsBar omits metrics with None values."""
    quote = Quote(
        symbol="TEST",
        name="Test Corp.",
        price=100.0,
        change=0.0,
        change_percent=0.0,
        volume=1000,
        market_cap=None,
        pe_ratio=25.0,
        eps=4.0,
    )
    widget = FundamentalsBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_fundamentals(quote)
        assert widget.display is True
        rendered = widget.query_one("#fundamentals-display").render().plain
        assert "P/E: 25.00" in rendered
        assert "EPS: $4.00" in rendered
        assert "Div:" not in rendered
        assert "Earnings:" not in rendered
        assert "50d:" not in rendered
        assert "200d:" not in rendered


@pytest.mark.asyncio
async def test_fundamentals_bar_hidden_when_all_none():
    """FundamentalsBar stays hidden when all fundamentals are None."""
    quote = Quote(
        symbol="TEST",
        name="Test Corp.",
        price=100.0,
        change=0.0,
        change_percent=0.0,
        volume=1000,
        market_cap=None,
    )
    widget = FundamentalsBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_fundamentals(quote)
        assert widget.display is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_widgets_coverage.py::test_fundamentals_bar_displays_metrics tests/test_widgets_coverage.py::test_fundamentals_bar_omits_none_fields tests/test_widgets_coverage.py::test_fundamentals_bar_hidden_when_all_none -v`
Expected: FAIL — module `fundamentals_bar` does not exist

- [ ] **Step 3: Create the FundamentalsBar widget**

Create `src/tenortui/widgets/fundamentals_bar.py`:

```python
from textual.widget import Widget
from textual.widgets import Static

from tenortui.models import Quote


class FundamentalsBar(Widget):
    DEFAULT_CSS = """
    FundamentalsBar {
        dock: top;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    FundamentalsBar #fundamentals-display {
        width: 1fr;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.display = False

    def compose(self):
        yield Static("", id="fundamentals-display")

    def show_fundamentals(self, quote: Quote) -> None:
        parts = []
        if quote.pe_ratio is not None:
            parts.append(f"P/E: {quote.pe_ratio:.2f}")
        if quote.eps is not None:
            parts.append(f"EPS: ${quote.eps:.2f}")
        if quote.dividend_yield is not None:
            parts.append(f"Div: {quote.dividend_yield:.2f}%")
        if quote.earnings_date is not None:
            parts.append(f"Earnings: {quote.earnings_date}")
        if quote.moving_avg_50d is not None:
            parts.append(f"50d: ${quote.moving_avg_50d:.2f}")
        if quote.moving_avg_200d is not None:
            parts.append(f"200d: ${quote.moving_avg_200d:.2f}")

        if not parts:
            self.display = False
            return

        self.query_one("#fundamentals-display").update(" | ".join(parts))
        self.display = True

    def hide(self) -> None:
        self.display = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_widgets_coverage.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/widgets/fundamentals_bar.py tests/test_widgets_coverage.py
git commit -m "feat: add FundamentalsBar widget

Single-line compact display of P/E, EPS, dividend yield,
earnings date, and moving averages. Hidden when all None.

Closes #11 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Wire FundamentalsBar into the App

**Files:**
- Modify: `src/tenortui/app.py:17,54-55,263-278`

- [ ] **Step 1: Add import and widget to compose()**

In `src/tenortui/app.py`:

Add import (after line 22, the `TickerBar` import):
```python
from tenortui.widgets.fundamentals_bar import FundamentalsBar
```

In `compose()` (line 55), add `FundamentalsBar()` between `TickerBar()` and the `Vertical`:
```python
def compose(self) -> ComposeResult:
    yield TickerBar()
    yield FundamentalsBar()
    with Vertical(id="main-content"):
        yield ExpirySelector()
        yield RecentlyViewed(symbols=self._history)
        yield ChainTable()
    yield StatusBar(provider_name=self._provider.name)
    yield CommandPalette()
```

- [ ] **Step 2: Wire into `_load_ticker()`**

At the start of `_load_ticker()` (after line 268 `chain_table.loading = True`), add:
```python
self.query_one(FundamentalsBar).hide()
```

After `ticker_bar.show_quote(quote)` (after line 278), add:
```python
self.query_one(FundamentalsBar).show_fundamentals(quote)
```

- [ ] **Step 3: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add src/tenortui/app.py
git commit -m "feat: wire FundamentalsBar into app layout and ticker loading

Show fundamentals after ticker load, hide on new load start
and on errors.

Closes #11

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Final Verification and Cleanup

- [ ] **Step 1: Run lint**

Run: `poetry run ruff check src/ tests/`
Expected: No errors

- [ ] **Step 2: Run format check**

Run: `poetry run ruff format --check src/ tests/`
Expected: No formatting issues (or run with `--fix` if needed)

- [ ] **Step 3: Run full test suite one final time**

Run: `poetry run python -m pytest -v`
Expected: ALL PASS

- [ ] **Step 4: Verify no uncommitted changes**

Run: `git status`
Expected: Clean working tree
