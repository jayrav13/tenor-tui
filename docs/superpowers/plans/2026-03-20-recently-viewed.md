# Recently Viewed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a navigable list of recently viewed tickers with live prices on the app's main page at launch.

**Architecture:** History is a JSON array of ticker symbols stored at `~/.config/tenor/history.json`. On launch, batch-fetch live quotes from Yahoo Finance for all history entries, display them in a selectable list widget. Config moves from `~/.tenorrc` to `~/.config/tenor/config.yaml` with backward compatibility.

**Tech Stack:** Python 3.11+, Textual (TUI framework), yfinance (batch quotes)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/tenortui/history.py` | Create | Read/write/update history JSON file |
| `src/tenortui/providers/yahoo.py` | Modify | Add `batch_quotes()` function |
| `src/tenortui/widgets/recently_viewed.py` | Create | Selectable list widget for recent tickers |
| `src/tenortui/config.py` | Modify | New default path `~/.config/tenor/config.yaml`, fallback to `~/.tenorrc` |
| `src/tenortui/app.py` | Modify | Integrate history + RecentlyViewed widget |
| `tests/test_history.py` | Create | Tests for history module |
| `tests/test_config.py` | Modify | Update tests for new config path + fallback |
| `tests/test_batch_quotes.py` | Create | Tests for batch quote fetching |
| `tests/test_app.py` | Modify | Tests for recently viewed integration |
| `README.md` | Modify | Update config path references |
| `CLAUDE.md` | Modify | Update config path references |

---

### Task 1: History Module

**Files:**
- Create: `src/tenortui/history.py`
- Create: `tests/test_history.py`

- [ ] **Step 1: Write failing tests for history module**

```python
# tests/test_history.py
import json
import pytest
from tenortui.history import load_history, save_history, add_to_history

MAX_HISTORY = 10


class TestLoadHistory:
    def test_no_file_returns_empty(self, tmp_path):
        result = load_history(tmp_path / "history.json")
        assert result == []

    def test_valid_file(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["AAPL", "MSFT"]))
        assert load_history(path) == ["AAPL", "MSFT"]

    def test_corrupt_file_returns_empty(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text("not json")
        assert load_history(path) == []

    def test_non_list_returns_empty(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"key": "val"}))
        assert load_history(path) == []


class TestSaveHistory:
    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "history.json"
        save_history(["AAPL"], path)
        assert json.loads(path.read_text()) == ["AAPL"]

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["OLD"]))
        save_history(["NEW"], path)
        assert json.loads(path.read_text()) == ["NEW"]


class TestAddToHistory:
    def test_adds_to_front(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["MSFT"]))
        result = add_to_history("AAPL", path)
        assert result == ["AAPL", "MSFT"]

    def test_dedupes_moves_to_front(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["AAPL", "MSFT", "GOOG"]))
        result = add_to_history("MSFT", path)
        assert result == ["MSFT", "AAPL", "GOOG"]

    def test_caps_at_max(self, tmp_path):
        path = tmp_path / "history.json"
        symbols = [f"SYM{i}" for i in range(MAX_HISTORY)]
        path.write_text(json.dumps(symbols))
        result = add_to_history("NEW", path)
        assert len(result) == MAX_HISTORY
        assert result[0] == "NEW"
        assert f"SYM{MAX_HISTORY - 1}" not in result

    def test_empty_history(self, tmp_path):
        path = tmp_path / "history.json"
        result = add_to_history("AAPL", path)
        assert result == ["AAPL"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenortui.history'`

- [ ] **Step 3: Implement history module**

```python
# src/tenortui/history.py
import json
from pathlib import Path

MAX_HISTORY = 10
DEFAULT_HISTORY_PATH = Path.home() / ".config" / "tenor" / "history.json"


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def save_history(symbols: list[str], path: Path = DEFAULT_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(symbols))


def add_to_history(symbol: str, path: Path = DEFAULT_HISTORY_PATH) -> list[str]:
    symbols = load_history(path)
    if symbol in symbols:
        symbols.remove(symbol)
    symbols.insert(0, symbol)
    symbols = symbols[:MAX_HISTORY]
    save_history(symbols, path)
    return symbols
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_history.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/history.py tests/test_history.py
git commit -m "feat: add history module for recently viewed tickers"
```

---

### Task 2: Config Path Migration

**Files:**
- Modify: `src/tenortui/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing test for new config path with fallback**

Add to `tests/test_config.py`:

```python
from tenortui.config import load_config, resolve_config_path


class TestConfigPathMigration:
    def test_new_config_path(self, tmp_path):
        config_dir = tmp_path / ".config" / "tenor"
        config_dir.mkdir(parents=True)
        cfg = config_dir / "config.yaml"
        cfg.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc123\n")
        config = load_config(config_path=cfg)
        assert config.provider_name == "tradier"

    def test_fallback_to_tenorrc(self, tmp_path):
        """When new path doesn't exist but ~/.tenorrc does, use it."""
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        old_path = tmp_path / ".tenorrc"
        old_path.write_text("---\ndefault: yahoo\n")
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == old_path

    def test_new_path_takes_precedence(self, tmp_path):
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        new_path.parent.mkdir(parents=True)
        new_path.write_text("---\ndefault: tradier\ntradier:\n  api_key: x\n")
        old_path = tmp_path / ".tenorrc"
        old_path.write_text("---\ndefault: yahoo\n")
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == new_path

    def test_neither_exists_returns_new_path(self, tmp_path):
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        old_path = tmp_path / ".tenorrc"
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == new_path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py::TestConfigPathMigration -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_config_path'`

- [ ] **Step 3: Update config.py**

Modify `src/tenortui/config.py`:
- Change `DEFAULT_CONFIG_PATH` to `Path.home() / ".config" / "tenor" / "config.yaml"`
- Add `LEGACY_CONFIG_PATH = Path.home() / ".tenorrc"`
- Add `resolve_config_path(new_path, legacy_path)` function that returns new_path if it exists, else legacy_path if it exists, else new_path
- Update `load_config` default to use `resolve_config_path()`
- Update error message in `load_config` that references `~/.tenorrc` to say `~/.config/tenor/config.yaml`

```python
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tenor" / "config.yaml"
LEGACY_CONFIG_PATH = Path.home() / ".tenorrc"


def resolve_config_path(
    new_path: Path = DEFAULT_CONFIG_PATH,
    legacy_path: Path = LEGACY_CONFIG_PATH,
) -> Path:
    if new_path.exists():
        return new_path
    if legacy_path.exists():
        return legacy_path
    return new_path


def load_config(
    config_path: Path | None = None,
    provider_override: str | None = None,
) -> AppConfig:
    if config_path is None:
        config_path = resolve_config_path()
    raw = _read_config_file(config_path)
    # ... rest unchanged
```

- [ ] **Step 4: Update existing tests that pass explicit paths**

Existing tests already pass explicit `tmp_path` paths so they should still work. Run full config test suite:

Run: `python -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/config.py tests/test_config.py
git commit -m "feat: migrate config path to ~/.config/tenor/config.yaml with fallback"
```

---

### Task 3: Batch Quote Fetching

**Files:**
- Modify: `src/tenortui/providers/yahoo.py`
- Create: `tests/test_batch_quotes.py`

- [ ] **Step 1: Write failing tests for batch_quotes**

```python
# tests/test_batch_quotes.py
from unittest.mock import patch, MagicMock
import pytest

from tenortui.providers.yahoo import batch_quotes
from tenortui.models import Quote


class TestBatchQuotes:
    def test_empty_list_returns_empty(self):
        assert batch_quotes([]) == []

    @patch("tenortui.providers.yahoo.yf")
    def test_returns_quotes_for_valid_symbols(self, mock_yf):
        tickers_mock = MagicMock()
        ticker_aapl = MagicMock()
        ticker_aapl.info = {
            "regularMarketPrice": 213.25,
            "shortName": "Apple Inc.",
            "regularMarketChange": 1.42,
            "regularMarketChangePercent": 0.67,
            "regularMarketVolume": 54200000,
            "marketCap": 3200000000000,
        }
        ticker_msft = MagicMock()
        ticker_msft.info = {
            "regularMarketPrice": 420.50,
            "shortName": "Microsoft Corporation",
            "regularMarketChange": -2.10,
            "regularMarketChangePercent": -0.50,
            "regularMarketVolume": 22000000,
            "marketCap": 3100000000000,
        }
        tickers_mock.tickers = {"AAPL": ticker_aapl, "MSFT": ticker_msft}
        mock_yf.Tickers.return_value = tickers_mock

        results = batch_quotes(["AAPL", "MSFT"])
        assert len(results) == 2
        assert results[0].symbol == "AAPL"
        assert results[0].price == 213.25
        assert results[1].symbol == "MSFT"

    @patch("tenortui.providers.yahoo.yf")
    def test_skips_failed_symbols(self, mock_yf):
        tickers_mock = MagicMock()
        ticker_aapl = MagicMock()
        ticker_aapl.info = {
            "regularMarketPrice": 213.25,
            "shortName": "Apple Inc.",
            "regularMarketChange": 1.42,
            "regularMarketChangePercent": 0.67,
            "regularMarketVolume": 54200000,
            "marketCap": 3200000000000,
        }
        ticker_bad = MagicMock()
        ticker_bad.info = {}
        tickers_mock.tickers = {"AAPL": ticker_aapl, "BAD": ticker_bad}
        mock_yf.Tickers.return_value = tickers_mock

        results = batch_quotes(["AAPL", "BAD"])
        assert len(results) == 1
        assert results[0].symbol == "AAPL"

    @patch("tenortui.providers.yahoo.yf")
    def test_handles_api_failure(self, mock_yf):
        mock_yf.Tickers.side_effect = Exception("network error")
        results = batch_quotes(["AAPL"])
        assert results == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_batch_quotes.py -v`
Expected: FAIL — `ImportError: cannot import name 'batch_quotes'`

- [ ] **Step 3: Implement batch_quotes in yahoo.py**

Add to end of `src/tenortui/providers/yahoo.py`:

```python
def batch_quotes(symbols: list[str]) -> list[Quote]:
    if not symbols:
        return []
    try:
        tickers = yf.Tickers(" ".join(symbols))
    except Exception:
        return []
    quotes = []
    for symbol in symbols:
        try:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                continue
            info = ticker.info
            if not info.get("regularMarketPrice"):
                continue
            quotes.append(Quote(
                symbol=symbol,
                name=info.get("shortName", symbol),
                price=info["regularMarketPrice"],
                change=info.get("regularMarketChange", 0.0),
                change_percent=info.get("regularMarketChangePercent", 0.0),
                volume=info.get("regularMarketVolume", 0),
                market_cap=info.get("marketCap"),
            ))
        except Exception:
            continue
    return quotes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_batch_quotes.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/providers/yahoo.py tests/test_batch_quotes.py
git commit -m "feat: add batch_quotes for fetching multiple ticker quotes"
```

---

### Task 4: RecentlyViewed Widget

**Files:**
- Create: `src/tenortui/widgets/recently_viewed.py`
- Modify: `src/tenortui/widgets/__init__.py`

- [ ] **Step 1: Implement RecentlyViewed widget**

```python
# src/tenortui/widgets/recently_viewed.py
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static, Label

from tenortui.models import Quote
from tenortui.widgets.ticker_bar import TickerBar


class RecentlyViewed(Widget):
    DEFAULT_CSS = """
    RecentlyViewed {
        height: 1fr;
    }
    RecentlyViewed .rv-title {
        text-style: bold;
        padding: 1 1 0 1;
        color: $text;
    }
    RecentlyViewed .rv-loading {
        padding: 0 1;
        color: $text-muted;
    }
    RecentlyViewed ListView {
        height: auto;
        max-height: 100%;
        padding: 0 1;
    }
    RecentlyViewed ListItem {
        height: 1;
        padding: 0 1;
    }
    RecentlyViewed .rv-empty {
        padding: 1;
        color: $text-muted;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, symbols: list[str] | None = None) -> None:
        super().__init__()
        self._symbols = symbols or []
        self._quotes: list[Quote] = []
        self._has_history = bool(self._symbols)

    def compose(self) -> ComposeResult:
        if not self._symbols:
            yield Static("Search for a ticker to view options chain", classes="rv-empty")
            return
        yield Static("Recently Viewed", classes="rv-title")
        yield Static("Loading quotes...", classes="rv-loading", id="rv-loading")
        yield ListView()

    def update_quotes(self, quotes: list[Quote]) -> None:
        self._quotes = quotes
        if self._has_history:
            self.query_one("#rv-loading", Static).display = False
            list_view = self.query_one(ListView)
            list_view.clear()
            for quote in quotes:
                change_sign = "+" if quote.change >= 0 else ""
                text = (
                    f"{quote.symbol:<6} {quote.name:<30} "
                    f"${quote.price:>10.2f}  "
                    f"{change_sign}{quote.change:.2f} ({change_sign}{quote.change_percent:.2f}%)"
                )
                list_view.append(ListItem(Label(text)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = self.query_one(ListView).index
        if index is not None and index < len(self._quotes):
            symbol = self._quotes[index].symbol
            self.post_message(TickerBar.TickerSubmitted(symbol))
```

- [ ] **Step 2: Run the app manually to verify widget renders**

Run: `tenortui` (visual check — should show empty state since no history yet)

- [ ] **Step 3: Commit**

```bash
git add src/tenortui/widgets/recently_viewed.py
git commit -m "feat: add RecentlyViewed widget for ticker selection"
```

---

### Task 5: App Integration

**Files:**
- Modify: `src/tenortui/app.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Integrate RecentlyViewed into app.py**

Modify `src/tenortui/app.py`:

1. Add imports:
```python
from tenortui.history import load_history, add_to_history
from tenortui.providers.yahoo import batch_quotes
from tenortui.widgets.recently_viewed import RecentlyViewed
```

2. Update `compose()` — replace `ChainTable()` with conditional:
```python
def compose(self) -> ComposeResult:
    yield TickerBar()
    with Vertical(id="main-content"):
        yield ExpirySelector()
        yield RecentlyViewed(symbols=self._history)
        yield ChainTable()
    yield StatusBar(provider_name=self._provider.name)
```

3. Update `__init__()` to load history:
```python
def __init__(self, provider):
    super().__init__()
    self._provider = provider
    self._current_symbol: str | None = None
    self._current_expiration: str | None = None
    self._current_price: float | None = None
    self._loading_ticker: bool = False
    self._history = load_history()
```

4. Update `on_mount()` to fetch batch quotes if history exists:
```python
def on_mount(self) -> None:
    self.query_one(TickerBar).focus_input()
    chain_table = self.query_one(ChainTable)
    recently_viewed = self.query_one(RecentlyViewed)
    if self._history:
        chain_table.display = False
        self._fetch_recent_quotes()
    else:
        recently_viewed.display = False
```

5. Add batch fetch worker:
```python
@work(exclusive=True, group="recent")
async def _fetch_recent_quotes(self) -> None:
    quotes = await asyncio.to_thread(batch_quotes, self._history)
    self.query_one(RecentlyViewed).update_quotes(quotes)
```

6. Update `_load_ticker` to hide RecentlyViewed and show ChainTable:
After the `chain_table.loading = True` line, add:
```python
recently_viewed = self.query_one(RecentlyViewed)
recently_viewed.display = False
chain_table.display = True
```

7. Update `_load_ticker` to save history after successful load — after `ticker_bar.show_quote(quote)`:
```python
self._history = add_to_history(symbol)
```

- [ ] **Step 2: Update test_app.py**

Add to `tests/test_app.py`:

```python
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.chain_table import ChainTable


@pytest.mark.asyncio
async def test_recently_viewed_hidden_when_no_history(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test() as pilot:
        rv = test_app.query_one(RecentlyViewed)
        assert rv.display is False


@pytest.mark.asyncio
async def test_recently_viewed_shown_when_history_exists(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: ["AAPL", "MSFT"])
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test() as pilot:
        rv = test_app.query_one(RecentlyViewed)
        ct = test_app.query_one(ChainTable)
        assert rv.display is True
        assert ct.display is False


@pytest.mark.asyncio
async def test_recently_viewed_hidden_after_ticker_load(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: ["AAPL"])
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: ["AAPL"])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test() as pilot:
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await test_app.workers.wait_for_complete()
        rv = test_app.query_one(RecentlyViewed)
        assert rv.display is False
```

- [ ] **Step 3: Run all tests**

Run: `python -m pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/tenortui/app.py tests/test_app.py
git commit -m "feat: integrate recently viewed into app with history persistence"
```

---

### Task 6: Update Docs

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update README.md**

- Change `~/.tenorrc` references to `~/.config/tenor/config.yaml`
- Add note about `~/.tenorrc` backward compatibility
- Add Recently Viewed section under Usage

- [ ] **Step 2: Update CLAUDE.md**

- Update config path references to `~/.config/tenor/`
- Add history.py to architecture notes

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: update config paths and add recently viewed docs"
```
