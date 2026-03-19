# TenorTUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python TUI for browsing stock options chains with pluggable data providers (Yahoo Finance, Tradier).

**Architecture:** Provider abstraction layer (`DataProvider` Protocol) with three methods. Textual app with four widget zones: ticker bar, expiry selector, chain tables, status bar. Sync provider calls dispatched via `run_worker(thread=True)` to avoid blocking the event loop.

**Tech Stack:** Python 3.11+, textual, yfinance, requests, pyyaml, pytest, pytest-asyncio

**Spec:** `docs/specs/2026-03-19-tenor-tui-design.md`

---

## File Structure

```
tenor-tui/
├── pyproject.toml                          # Package config, deps, entry point
├── README.md
├── src/
│   └── tenortui/
│       ├── __init__.py                     # Version string
│       ├── app.py                          # TenorTUI App class, main(), keybindings, worker dispatch
│       ├── config.py                       # Load ~/.tenorrc, parse CLI args, return provider instance
│       ├── exceptions.py                   # ProviderError, SymbolNotFoundError, ConfigError
│       ├── models.py                       # Quote, OptionContract (@property mid), OptionsChain
│       ├── providers/
│       │   ├── __init__.py                 # PROVIDERS registry dict
│       │   ├── base.py                     # DataProvider Protocol definition
│       │   ├── yahoo.py                    # YahooProvider using yfinance
│       │   └── tradier.py                  # TradierProvider using requests
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── ticker_bar.py              # Input + quote label composite widget
│       │   ├── expiry_selector.py         # Horizontal tab strip for expiration dates
│       │   ├── chain_table.py             # DataTable for calls/puts with ATM divider
│       │   └── status_bar.py              # Provider name, keybindings, last refresh time
│       └── styles/
│           └── app.tcss                    # Textual CSS for layout and colors
├── tests/
│   ├── conftest.py                         # Shared fixtures (fake provider, sample data)
│   ├── fixtures/
│   │   ├── yahoo_quote.json               # Sample yfinance ticker.info response
│   │   ├── yahoo_chain.json               # Sample yfinance option_chain response
│   │   ├── tradier_quote.json             # Sample Tradier /markets/quotes response
│   │   ├── tradier_expirations.json       # Sample Tradier /markets/options/expirations response
│   │   └── tradier_chain.json             # Sample Tradier /markets/options/chains response
│   ├── test_models.py                      # Quote, OptionContract, OptionsChain tests
│   ├── test_config.py                      # Config loading and validation tests
│   ├── test_yahoo_provider.py              # Yahoo provider with mocked yfinance
│   ├── test_tradier_provider.py            # Tradier provider with mocked requests
│   └── test_app.py                         # Integration tests with Textual Pilot
└── docs/
    ├── specs/
    │   └── 2026-03-19-tenor-tui-design.md
    └── plans/
        └── 2026-03-19-tenor-tui-plan.md
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/tenortui/__init__.py`
- Create: `src/tenortui/exceptions.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tenor-tui"
version = "0.1.0"
description = "A terminal UI for browsing stock options chains"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50",
    "yfinance>=0.2.30",
    "requests>=2.28",
    "pyyaml>=6.0",
]

[project.scripts]
tenortui = "tenortui.app:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pandas",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

- [ ] **Step 2: Create `src/tenortui/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `src/tenortui/exceptions.py`**

```python
class ProviderError(Exception):
    """Base exception for all provider errors."""


class SymbolNotFoundError(ProviderError):
    """Raised when a ticker symbol is not recognized by the provider."""


class ConfigError(Exception):
    """Raised for config file parsing or validation errors."""
```

- [ ] **Step 4: Create `.gitignore`**

```gitignore
__pycache__/
*.egg-info/
.venv/
.pytest_cache/
dist/
build/
*.pyc
```

- [ ] **Step 5: Create empty `tests/conftest.py`**

```python
# Shared test fixtures — populated in later tasks
```

- [ ] **Step 6: Install in dev mode and verify**

Run: `cd /Users/jravaliya/Code/tenor-tui && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
Expected: installs successfully, `tenortui` command registered (will fail at runtime since `app.py` doesn't exist yet)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore src/ tests/conftest.py
git commit -m "feat: project scaffolding with pyproject.toml and exceptions"
```

---

### Task 2: Data Models

**Files:**
- Create: `src/tenortui/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/test_models.py`:

```python
from tenortui.models import Quote, OptionContract, OptionsChain


class TestQuote:
    def test_create_quote(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
        )
        assert q.symbol == "AAPL"
        assert q.price == 213.25

    def test_quote_market_cap_optional(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=None,
        )
        assert q.market_cap is None


class TestOptionContract:
    def test_mid_property(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=0.81,
            gamma=0.03,
            theta=-0.15,
            vega=0.25,
            rho=0.10,
        )
        assert c.mid == (14.20 + 14.50) / 2

    def test_mid_with_zero_bid_ask(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00500000",
            option_type="call",
            strike=500.0,
            bid=0.0,
            ask=0.01,
            last_price=0.01,
            volume=0,
            open_interest=0,
            implied_volatility=0.0,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert c.mid == 0.005

    def test_greeks_optional(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert c.delta is None
        assert c.gamma is None

    def test_has_greeks(self):
        with_greeks = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=0.81,
            gamma=0.03,
            theta=-0.15,
            vega=0.25,
            rho=0.10,
        )
        without_greeks = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert with_greeks.has_greeks is True
        assert without_greeks.has_greeks is False


class TestOptionsChain:
    def test_create_chain(self):
        chain = OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=[], puts=[])
        assert chain.symbol == "AAPL"
        assert chain.expiration == "2026-03-21"
        assert chain.calls == []
        assert chain.puts == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/jravaliya/Code/tenor-tui && source .venv/bin/activate && python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tenortui.models'`

- [ ] **Step 3: Implement models**

Create `src/tenortui/models.py`:

```python
from dataclasses import dataclass


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: float | None


@dataclass
class OptionContract:
    contract_symbol: str
    option_type: str
    strike: float
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    rho: float | None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def has_greeks(self) -> bool:
        return self.delta is not None


@dataclass
class OptionsChain:
    symbol: str
    expiration: str
    calls: list[OptionContract]
    puts: list[OptionContract]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/models.py tests/test_models.py
git commit -m "feat: add data models (Quote, OptionContract, OptionsChain)"
```

---

### Task 3: Provider Protocol & Registry

**Files:**
- Create: `src/tenortui/providers/__init__.py`
- Create: `src/tenortui/providers/base.py`

- [ ] **Step 1: Create provider protocol**

Create `src/tenortui/providers/base.py`:

```python
from typing import Protocol

from tenortui.models import Quote, OptionsChain


class DataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
```

- [ ] **Step 2: Create provider registry (empty for now)**

Create `src/tenortui/providers/__init__.py`:

```python
from tenortui.providers.base import DataProvider

PROVIDERS: dict[str, type] = {}
```

- [ ] **Step 3: Commit**

```bash
git add src/tenortui/providers/
git commit -m "feat: add DataProvider protocol and provider registry"
```

---

### Task 4: Configuration

**Files:**
- Create: `src/tenortui/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

Create `tests/test_config.py`:

```python
import pytest
from unittest.mock import patch
from pathlib import Path

from tenortui.config import load_config
from tenortui.exceptions import ConfigError


class TestLoadConfig:
    def test_no_config_file_defaults_to_yahoo(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.provider_name == "yahoo"
        assert config.provider_config == {}

    def test_valid_yaml_with_default(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc123\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "tradier"
        assert config.provider_config == {"api_key": "abc123"}

    def test_valid_yaml_no_default_uses_first_provider(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "yahoo"

    def test_cli_override(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: yahoo\nyahoo: {}\n")
        config = load_config(config_path=rc, provider_override="tradier")
        assert config.provider_name == "tradier"

    def test_malformed_yaml_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text(":{bad yaml")
        with pytest.raises(ConfigError):
            load_config(config_path=rc)

    def test_unknown_provider_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: nonexistent\n")
        with pytest.raises(ConfigError, match="Unknown provider"):
            load_config(config_path=rc)

    def test_tradier_missing_api_key_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier: {}\n")
        with pytest.raises(ConfigError, match="api_key"):
            load_config(config_path=rc)

    def test_no_default_uses_first_provider_key(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ntradier:\n  api_key: abc\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "tradier"  # first in file

    def test_tradier_sandbox_defaults_false(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc\n")
        config = load_config(config_path=rc)
        assert config.provider_config.get("sandbox", False) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tenortui.config'`

- [ ] **Step 3: Implement config**

Create `src/tenortui/config.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tenortui.exceptions import ConfigError

KNOWN_PROVIDERS = {"yahoo", "tradier"}
DEFAULT_CONFIG_PATH = Path.home() / ".tenorrc"

PROVIDER_REQUIRED_FIELDS: dict[str, list[str]] = {
    "yahoo": [],
    "tradier": ["api_key"],
}


@dataclass
class AppConfig:
    provider_name: str
    provider_config: dict = field(default_factory=dict)


def load_config(
    config_path: Path = DEFAULT_CONFIG_PATH,
    provider_override: str | None = None,
) -> AppConfig:
    raw = _read_config_file(config_path)

    if provider_override:
        provider_name = provider_override
    elif "default" in raw:
        provider_name = raw["default"]
    else:
        provider_keys = [k for k in raw if k in KNOWN_PROVIDERS]
        provider_name = provider_keys[0] if provider_keys else "yahoo"

    if provider_name not in KNOWN_PROVIDERS:
        raise ConfigError(
            f"Unknown provider '{provider_name}'. "
            f"Available: {', '.join(sorted(KNOWN_PROVIDERS))}"
        )

    provider_config = raw.get(provider_name, {}) or {}

    for req_field in PROVIDER_REQUIRED_FIELDS.get(provider_name, []):
        if req_field not in provider_config:
            raise ConfigError(
                f"Provider '{provider_name}' requires '{req_field}' in ~/.tenorrc"
            )

    return AppConfig(provider_name=provider_name, provider_config=provider_config)


def _read_config_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse {path}: {e}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/config.py tests/test_config.py
git commit -m "feat: add config loading from ~/.tenorrc with validation"
```

---

### Task 5: Yahoo Provider

**Files:**
- Create: `src/tenortui/providers/yahoo.py`
- Create: `tests/test_yahoo_provider.py`
- Create: `tests/fixtures/yahoo_quote.json`
- Create: `tests/fixtures/yahoo_chain.json`
- Modify: `src/tenortui/providers/__init__.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/yahoo_quote.json`:

```json
{
  "shortName": "Apple Inc.",
  "regularMarketPrice": 213.25,
  "regularMarketChange": 1.42,
  "regularMarketChangePercent": 0.67,
  "regularMarketVolume": 54200000,
  "marketCap": 3200000000000
}
```

Create `tests/fixtures/yahoo_chain.json` — this file simulates what `yfinance`'s `option_chain()` returns. Since `yfinance` returns a named tuple with `.calls` and `.puts` DataFrames, we store the raw data to build mock DataFrames:

```json
{
  "calls": [
    {
      "contractSymbol": "AAPL260321C00200000",
      "strike": 200.0,
      "bid": 14.20,
      "ask": 14.50,
      "lastPrice": 14.35,
      "volume": 1234,
      "openInterest": 8901,
      "impliedVolatility": 0.32
    },
    {
      "contractSymbol": "AAPL260321C00210000",
      "strike": 210.0,
      "bid": 6.30,
      "ask": 6.55,
      "lastPrice": 6.43,
      "volume": 2341,
      "openInterest": 12034,
      "impliedVolatility": 0.27
    }
  ],
  "puts": [
    {
      "contractSymbol": "AAPL260321P00200000",
      "strike": 200.0,
      "bid": 0.85,
      "ask": 0.95,
      "lastPrice": 0.90,
      "volume": 567,
      "openInterest": 3456,
      "impliedVolatility": 0.28
    }
  ]
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_yahoo_provider.py`:

```python
import json
from pathlib import Path
from collections import namedtuple
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from tenortui.providers.yahoo import YahooProvider
from tenortui.exceptions import SymbolNotFoundError
from tenortui.models import Quote, OptionsChain

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_ticker(info: dict, options: tuple[str, ...] = (), chain_data: dict | None = None):
    ticker = MagicMock()
    ticker.info = info
    ticker.options = options

    if chain_data:
        OptionChain = namedtuple("OptionChain", ["calls", "puts"])
        calls_df = pd.DataFrame(chain_data["calls"])
        puts_df = pd.DataFrame(chain_data["puts"])
        ticker.option_chain.return_value = OptionChain(calls=calls_df, puts=puts_df)

    return ticker


class TestYahooProviderGetQuote:
    def test_returns_quote(self):
        info = _load_fixture("yahoo_quote.json")
        provider = YahooProvider()

        with patch("tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)):
            quote = provider.get_quote("AAPL")

        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 213.25
        assert quote.change == 1.42
        assert quote.volume == 54200000

    def test_symbol_not_found(self):
        ticker = MagicMock()
        ticker.info = {"regularMarketPrice": None}
        provider = YahooProvider()

        with patch("tenortui.providers.yahoo.yf.Ticker", return_value=ticker):
            with pytest.raises(SymbolNotFoundError):
                provider.get_quote("FAKESYMBOL")


class TestYahooProviderGetExpirations:
    def test_returns_expirations(self):
        expirations = ("2026-03-21", "2026-03-28", "2026-04-04")
        provider = YahooProvider()

        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            return_value=_mock_ticker({}, options=expirations),
        ):
            result = provider.get_expirations("AAPL")

        assert result == ["2026-03-21", "2026-03-28", "2026-04-04"]


class TestYahooProviderGetChain:
    def test_returns_chain(self):
        chain_data = _load_fixture("yahoo_chain.json")
        provider = YahooProvider()

        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            return_value=_mock_ticker({}, chain_data=chain_data),
        ):
            chain = provider.get_chain("AAPL", "2026-03-21")

        assert isinstance(chain, OptionsChain)
        assert chain.symbol == "AAPL"
        assert chain.expiration == "2026-03-21"
        assert len(chain.calls) == 2
        assert len(chain.puts) == 1
        assert chain.calls[0].strike == 200.0
        assert chain.calls[0].bid == 14.20
        assert chain.calls[0].delta is None  # Yahoo doesn't provide greeks
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_yahoo_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tenortui.providers.yahoo'`

- [ ] **Step 4: Implement Yahoo provider**

Create `src/tenortui/providers/yahoo.py`:

```python
import yfinance as yf

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote


class YahooProvider:
    name = "yahoo"

    def get_quote(self, symbol: str) -> Quote:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
        except Exception as e:
            raise ProviderError(f"Failed to fetch quote for {symbol}: {e}") from e

        if not info.get("regularMarketPrice"):
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found")

        return Quote(
            symbol=symbol.upper(),
            name=info.get("shortName", symbol),
            price=info["regularMarketPrice"],
            change=info.get("regularMarketChange", 0.0),
            change_percent=info.get("regularMarketChangePercent", 0.0),
            volume=info.get("regularMarketVolume", 0),
            market_cap=info.get("marketCap"),
        )

    def get_expirations(self, symbol: str) -> list[str]:
        try:
            ticker = yf.Ticker(symbol)
            return list(ticker.options)
        except Exception as e:
            raise ProviderError(f"Failed to fetch expirations for {symbol}: {e}") from e

    def get_chain(self, symbol: str, expiration: str) -> OptionsChain:
        try:
            ticker = yf.Ticker(symbol)
            chain = ticker.option_chain(expiration)
        except Exception as e:
            raise ProviderError(
                f"Failed to fetch chain for {symbol} {expiration}: {e}"
            ) from e

        return OptionsChain(
            symbol=symbol.upper(),
            expiration=expiration,
            calls=[self._row_to_contract(row, "call") for _, row in chain.calls.iterrows()],
            puts=[self._row_to_contract(row, "put") for _, row in chain.puts.iterrows()],
        )

    @staticmethod
    def _row_to_contract(row, option_type: str) -> OptionContract:
        return OptionContract(
            contract_symbol=row.get("contractSymbol", ""),
            option_type=option_type,
            strike=float(row.get("strike", 0)),
            bid=float(row.get("bid", 0)),
            ask=float(row.get("ask", 0)),
            last_price=float(row.get("lastPrice", 0)),
            volume=int(row.get("volume", 0) or 0),
            open_interest=int(row.get("openInterest", 0) or 0),
            implied_volatility=float(row.get("impliedVolatility", 0)),
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
```

- [ ] **Step 5: Register Yahoo in providers `__init__`**

Update `src/tenortui/providers/__init__.py`:

```python
from tenortui.providers.base import DataProvider
from tenortui.providers.yahoo import YahooProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_yahoo_provider.py -v`
Expected: all 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/providers/ tests/test_yahoo_provider.py tests/fixtures/
git commit -m "feat: add Yahoo Finance provider with yfinance"
```

---

### Task 6: Tradier Provider

**Files:**
- Create: `src/tenortui/providers/tradier.py`
- Create: `tests/test_tradier_provider.py`
- Create: `tests/fixtures/tradier_quote.json`
- Create: `tests/fixtures/tradier_expirations.json`
- Create: `tests/fixtures/tradier_chain.json`
- Modify: `src/tenortui/providers/__init__.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/fixtures/tradier_quote.json`:

```json
{
  "quotes": {
    "quote": {
      "symbol": "AAPL",
      "description": "Apple Inc.",
      "last": 213.25,
      "change": 1.42,
      "change_percentage": 0.67,
      "volume": 54200000,
      "market_cap": 3200000000000
    }
  }
}
```

Create `tests/fixtures/tradier_expirations.json`:

```json
{
  "expirations": {
    "date": ["2026-03-21", "2026-03-28", "2026-04-04"]
  }
}
```

Create `tests/fixtures/tradier_chain.json`:

```json
{
  "options": {
    "option": [
      {
        "symbol": "AAPL260321C00200000",
        "option_type": "call",
        "strike": 200.0,
        "bid": 14.20,
        "ask": 14.50,
        "last": 14.35,
        "volume": 1234,
        "open_interest": 8901,
        "implied_volatility": 0.32,
        "greeks": {
          "delta": 0.81,
          "gamma": 0.03,
          "theta": -0.15,
          "vega": 0.25,
          "rho": 0.10
        }
      },
      {
        "symbol": "AAPL260321P00200000",
        "option_type": "put",
        "strike": 200.0,
        "bid": 0.85,
        "ask": 0.95,
        "last": 0.90,
        "volume": 567,
        "open_interest": 3456,
        "implied_volatility": 0.28,
        "greeks": {
          "delta": -0.18,
          "gamma": 0.02,
          "theta": -0.10,
          "vega": 0.20,
          "rho": -0.05
        }
      }
    ]
  }
}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_tradier_provider.py`:

```python
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tenortui.providers.tradier import TradierProvider
from tenortui.exceptions import SymbolNotFoundError, ProviderError
from tenortui.models import Quote, OptionsChain

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_response(json_data: dict, status_code: int = 200):
    import requests as req
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.side_effect = (
        None if status_code == 200 else req.exceptions.HTTPError(f"HTTP {status_code}")
    )
    return resp


class TestTradierProviderGetQuote:
    def test_returns_quote(self):
        data = _load_fixture("tradier_quote.json")
        provider = TradierProvider(api_key="test", sandbox=False)

        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            quote = provider.get_quote("AAPL")

        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 213.25
        assert quote.change == 1.42

    def test_symbol_not_found(self):
        data = {"quotes": {"unmatched_symbols": {"symbol": ["FAKESYMBOL"]}}}
        provider = TradierProvider(api_key="test", sandbox=False)

        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            with pytest.raises(SymbolNotFoundError):
                provider.get_quote("FAKESYMBOL")

    def test_sandbox_url(self):
        provider = TradierProvider(api_key="test", sandbox=True)
        assert "sandbox" in provider._base_url


class TestTradierProviderGetExpirations:
    def test_returns_expirations(self):
        data = _load_fixture("tradier_expirations.json")
        provider = TradierProvider(api_key="test", sandbox=False)

        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            result = provider.get_expirations("AAPL")

        assert result == ["2026-03-21", "2026-03-28", "2026-04-04"]


class TestTradierProviderGetChain:
    def test_returns_chain_with_greeks(self):
        data = _load_fixture("tradier_chain.json")
        provider = TradierProvider(api_key="test", sandbox=False)

        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            chain = provider.get_chain("AAPL", "2026-03-21")

        assert isinstance(chain, OptionsChain)
        assert len(chain.calls) == 1
        assert len(chain.puts) == 1
        assert chain.calls[0].delta == 0.81
        assert chain.calls[0].gamma == 0.03
        assert chain.puts[0].delta == -0.18
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_tradier_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tenortui.providers.tradier'`

- [ ] **Step 4: Implement Tradier provider**

Create `src/tenortui/providers/tradier.py`:

```python
import requests

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote

PROD_URL = "https://api.tradier.com/v1"
SANDBOX_URL = "https://sandbox.tradier.com/v1"


class TradierProvider:
    name = "tradier"

    def __init__(self, api_key: str, sandbox: bool = False):
        self._api_key = api_key
        self._base_url = SANDBOX_URL if sandbox else PROD_URL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            resp = requests.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise ProviderError(f"Tradier API error: {e}") from e

    def get_quote(self, symbol: str) -> Quote:
        data = self._get("/markets/quotes", params={"symbols": symbol})
        quotes = data.get("quotes", {})

        if "unmatched_symbols" in quotes:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found")

        q = quotes.get("quote", {})
        return Quote(
            symbol=q["symbol"],
            name=q.get("description", symbol),
            price=float(q.get("last", 0)),
            change=float(q.get("change", 0)),
            change_percent=float(q.get("change_percentage", 0)),
            volume=int(q.get("volume", 0) or 0),
            market_cap=q.get("market_cap"),
        )

    def get_expirations(self, symbol: str) -> list[str]:
        data = self._get("/markets/options/expirations", params={"symbol": symbol})
        dates = data.get("expirations", {}).get("date", [])
        return dates if isinstance(dates, list) else [dates]

    def get_chain(self, symbol: str, expiration: str) -> OptionsChain:
        data = self._get(
            "/markets/options/chains",
            params={"symbol": symbol, "expiration": expiration, "greeks": "true"},
        )
        options = data.get("options", {}).get("option", [])

        calls = []
        puts = []
        for opt in options:
            contract = self._to_contract(opt)
            if contract.option_type == "call":
                calls.append(contract)
            else:
                puts.append(contract)

        return OptionsChain(
            symbol=symbol.upper(),
            expiration=expiration,
            calls=calls,
            puts=puts,
        )

    @staticmethod
    def _to_contract(opt: dict) -> OptionContract:
        greeks = opt.get("greeks") or {}
        return OptionContract(
            contract_symbol=opt.get("symbol", ""),
            option_type=opt.get("option_type", "call"),
            strike=float(opt.get("strike", 0)),
            bid=float(opt.get("bid", 0)),
            ask=float(opt.get("ask", 0)),
            last_price=float(opt.get("last", 0)),
            volume=int(opt.get("volume", 0) or 0),
            open_interest=int(opt.get("open_interest", 0) or 0),
            implied_volatility=float(opt.get("implied_volatility", 0) or 0),
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            theta=greeks.get("theta"),
            vega=greeks.get("vega"),
            rho=greeks.get("rho"),
        )
```

- [ ] **Step 5: Register Tradier in providers `__init__`**

Update `src/tenortui/providers/__init__.py`:

```python
from tenortui.providers.base import DataProvider
from tenortui.providers.yahoo import YahooProvider
from tenortui.providers.tradier import TradierProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
    "tradier": TradierProvider,
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_tradier_provider.py -v`
Expected: all 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/providers/ tests/test_tradier_provider.py tests/fixtures/tradier_*.json
git commit -m "feat: add Tradier provider with greeks support"
```

---

### Task 7: Shared Test Fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add shared fixtures for use in widget/integration tests**

Update `tests/conftest.py`:

```python
import pytest

from tenortui.models import Quote, OptionContract, OptionsChain


@pytest.fixture
def sample_quote():
    return Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=213.25,
        change=1.42,
        change_percent=0.67,
        volume=54_200_000,
        market_cap=3_200_000_000_000,
    )


@pytest.fixture
def sample_chain():
    calls = [
        OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        ),
        OptionContract(
            contract_symbol="AAPL260321C00210000",
            option_type="call",
            strike=210.0,
            bid=6.30,
            ask=6.55,
            last_price=6.43,
            volume=2341,
            open_interest=12034,
            implied_volatility=0.27,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        ),
        OptionContract(
            contract_symbol="AAPL260321C00220000",
            option_type="call",
            strike=220.0,
            bid=1.50,
            ask=1.65,
            last_price=1.58,
            volume=1876,
            open_interest=9012,
            implied_volatility=0.24,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        ),
    ]
    puts = [
        OptionContract(
            contract_symbol="AAPL260321P00200000",
            option_type="put",
            strike=200.0,
            bid=0.85,
            ask=0.95,
            last_price=0.90,
            volume=567,
            open_interest=3456,
            implied_volatility=0.28,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        ),
    ]
    return OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=calls, puts=puts)


@pytest.fixture
def sample_expirations():
    return ["2026-03-21", "2026-03-28", "2026-04-04", "2026-04-17"]


class FakeProvider:
    """Test provider that returns canned data without hitting any API."""
    name = "fake"

    def __init__(self, quote, expirations, chain):
        self._quote = quote
        self._expirations = expirations
        self._chain = chain

    def get_quote(self, symbol):
        return self._quote

    def get_expirations(self, symbol):
        return self._expirations

    def get_chain(self, symbol, expiration):
        return self._chain


@pytest.fixture
def fake_provider(sample_quote, sample_expirations, sample_chain):
    return FakeProvider(sample_quote, sample_expirations, sample_chain)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `python -m pytest -v`
Expected: all existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: add shared test fixtures and FakeProvider"
```

---

### Task 8: Status Bar Widget

**Files:**
- Create: `src/tenortui/widgets/__init__.py`
- Create: `src/tenortui/widgets/status_bar.py`

- [ ] **Step 1: Create widgets package**

Create `src/tenortui/widgets/__init__.py`:

```python
```

- [ ] **Step 2: Implement status bar**

Create `src/tenortui/widgets/status_bar.py`:

```python
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
    }
    StatusBar Horizontal {
        width: 1fr;
        height: 1;
    }
    StatusBar .status-provider {
        width: auto;
        padding: 0 1;
        color: $accent;
    }
    StatusBar .status-keys {
        width: 1fr;
        padding: 0 1;
    }
    StatusBar .status-time {
        width: auto;
        padding: 0 1;
    }
    """

    def __init__(self, provider_name: str = ""):
        super().__init__()
        self._provider_name = provider_name
        self._last_refresh: str = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(self._provider_name, classes="status-provider")
            yield Static(
                "Ctrl+R: Refresh | /: Search | q: Quit",
                classes="status-keys",
            )
            yield Static(self._last_refresh, classes="status-time", id="status-time")

    def update_refresh_time(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self._last_refresh = f"Last: {now}"
        try:
            self.query_one("#status-time", Static).update(self._last_refresh)
        except Exception:
            pass
```

- [ ] **Step 3: Commit**

```bash
git add src/tenortui/widgets/
git commit -m "feat: add StatusBar widget"
```

---

### Task 9: Ticker Bar Widget

**Files:**
- Create: `src/tenortui/widgets/ticker_bar.py`

- [ ] **Step 1: Implement ticker bar**

Create `src/tenortui/widgets/ticker_bar.py`:

```python
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static

from tenortui.models import Quote


class TickerBar(Widget):
    DEFAULT_CSS = """
    TickerBar {
        dock: top;
        height: 3;
        background: $surface;
        padding: 0 1;
    }
    TickerBar Horizontal {
        height: 3;
        align: left middle;
    }
    TickerBar Input {
        width: 12;
        margin: 0 1 0 0;
    }
    TickerBar .quote-info {
        width: 1fr;
        padding: 0 1;
    }
    TickerBar .error-message {
        width: 1fr;
        padding: 0 1;
        color: $error;
    }
    """

    class TickerSubmitted(Message):
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="Ticker...", id="ticker-input")
            yield Static("", id="quote-display", classes="quote-info")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        symbol = event.value.strip().upper()
        if symbol:
            self.post_message(self.TickerSubmitted(symbol))

    def show_quote(self, quote: Quote) -> None:
        change_sign = "+" if quote.change >= 0 else ""
        text = (
            f"{quote.name}  "
            f"${quote.price:.2f}  "
            f"{change_sign}{quote.change:.2f} "
            f"({change_sign}{quote.change_percent:.2f}%)"
        )
        display = self.query_one("#quote-display", Static)
        display.remove_class("error-message")
        display.add_class("quote-info")
        display.update(text)

    def show_error(self, message: str) -> None:
        display = self.query_one("#quote-display", Static)
        display.remove_class("quote-info")
        display.add_class("error-message")
        display.update(message)

    def focus_input(self) -> None:
        self.query_one("#ticker-input", Input).focus()
```

- [ ] **Step 2: Commit**

```bash
git add src/tenortui/widgets/ticker_bar.py
git commit -m "feat: add TickerBar widget with search and quote display"
```

---

### Task 10: Expiry Selector Widget

**Files:**
- Create: `src/tenortui/widgets/expiry_selector.py`

- [ ] **Step 1: Implement expiry selector**

Create `src/tenortui/widgets/expiry_selector.py`:

```python
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TabbedContent, TabPane


class ExpirySelector(Widget):
    DEFAULT_CSS = """
    ExpirySelector {
        height: auto;
        max-height: 5;
    }
    ExpirySelector TabbedContent {
        height: auto;
        max-height: 5;
    }
    ExpirySelector .no-data {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    class ExpirySelected(Message):
        def __init__(self, expiration: str) -> None:
            self.expiration = expiration
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("Search for a ticker to view options", classes="no-data")

    def set_expirations(self, expirations: list[str]) -> None:
        # Remove existing children
        for child in list(self.children):
            child.remove()

        if not expirations:
            self.mount(Static("No options available", classes="no-data"))
            return

        # Build TabbedContent with explicit TabPane objects
        tabbed = TabbedContent(id="expiry-tabs")
        self.mount(tabbed)
        for exp in expirations:
            tabbed.add_pane(TabPane(exp, Static(""), id=f"exp-{exp}"))

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        label = str(event.tab.label)
        self.post_message(self.ExpirySelected(label))

    def show_message(self, text: str) -> None:
        for child in list(self.children):
            child.remove()
        self.mount(Static(text, classes="no-data"))
```

- [ ] **Step 2: Commit**

```bash
git add src/tenortui/widgets/expiry_selector.py
git commit -m "feat: add ExpirySelector widget with tab switching"
```

---

### Task 11: Chain Table Widget

**Files:**
- Create: `src/tenortui/widgets/chain_table.py`

- [ ] **Step 1: Implement chain table**

Create `src/tenortui/widgets/chain_table.py`:

```python
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import DataTable, Static

from tenortui.models import OptionContract, OptionsChain


BASE_COLUMNS = [
    ("Strike", 10),
    ("Bid", 8),
    ("Ask", 8),
    ("Mid", 8),
    ("Last", 8),
    ("Vol", 8),
    ("OI", 8),
    ("IV", 8),
]

GREEK_COLUMNS = [
    ("Delta", 8),
    ("Gamma", 8),
    ("Theta", 8),
    ("Vega", 8),
    ("Rho", 8),
]


class ChainTable(Widget):
    DEFAULT_CSS = """
    ChainTable {
        height: 1fr;
    }
    ChainTable Vertical {
        height: 1fr;
    }
    ChainTable .section-label {
        height: 1;
        text-style: bold;
        padding: 0 1;
        background: $primary-background;
        color: $text;
        text-align: center;
        width: 1fr;
    }
    ChainTable DataTable {
        height: 1fr;
    }
    ChainTable .no-data {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Search for a ticker to view options chain", classes="no-data", id="chain-placeholder")

    def display_chain(self, chain: OptionsChain, current_price: float | None = None) -> None:
        # Determine if we show greeks
        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        columns = BASE_COLUMNS + (GREEK_COLUMNS if show_greeks else [])

        # Remove existing children
        container = self.query_one(Vertical)
        for child in list(container.children):
            child.remove()

        # Calls section
        container.mount(Static("CALLS", classes="section-label"))
        calls_table = DataTable(id="calls-table")
        container.mount(calls_table)
        self._populate_table(calls_table, columns, chain.calls, current_price)

        # Puts section
        container.mount(Static("PUTS", classes="section-label"))
        puts_table = DataTable(id="puts-table")
        container.mount(puts_table)
        self._populate_table(puts_table, columns, chain.puts, current_price)

    def _populate_table(
        self,
        table: DataTable,
        columns: list[tuple[str, int]],
        contracts: list[OptionContract],
        current_price: float | None,
    ) -> None:
        for col_name, _width in columns:
            table.add_column(col_name, key=col_name.lower())

        atm_inserted = False
        for contract in sorted(contracts, key=lambda c: c.strike):
            # Insert ATM divider
            if current_price and not atm_inserted and contract.strike > current_price:
                atm_row = ["── ATM ──"] + ["─" * 6] * (len(columns) - 1)
                table.add_row(*atm_row)
                atm_inserted = True

            row = [
                f"{contract.strike:.2f}",
                f"{contract.bid:.2f}",
                f"{contract.ask:.2f}",
                f"{contract.mid:.2f}",
                f"{contract.last_price:.2f}",
                f"{contract.volume:,}",
                f"{contract.open_interest:,}",
                f"{contract.implied_volatility:.2%}",
            ]
            if any(col[0] in ("Delta", "Gamma", "Theta", "Vega", "Rho") for col in columns):
                row.extend([
                    f"{contract.delta:.3f}" if contract.delta is not None else "",
                    f"{contract.gamma:.3f}" if contract.gamma is not None else "",
                    f"{contract.theta:.3f}" if contract.theta is not None else "",
                    f"{contract.vega:.3f}" if contract.vega is not None else "",
                    f"{contract.rho:.3f}" if contract.rho is not None else "",
                ])
            table.add_row(*row)

    def show_message(self, text: str) -> None:
        container = self.query_one(Vertical)
        for child in list(container.children):
            child.remove()
        container.mount(Static(text, classes="no-data", id="chain-placeholder"))
```

- [ ] **Step 2: Commit**

```bash
git add src/tenortui/widgets/chain_table.py
git commit -m "feat: add ChainTable widget with ATM divider and conditional greeks"
```

---

### Task 12: Textual CSS

**Files:**
- Create: `src/tenortui/styles/app.tcss`

- [ ] **Step 1: Create app stylesheet**

Create `src/tenortui/styles/app.tcss`:

```tcss
Screen {
    background: $surface;
    color: $text;
    layout: vertical;
}

#main-content {
    height: 1fr;
    layout: vertical;
}

LoadingIndicator {
    background: $surface 50%;
}
```

- [ ] **Step 2: Commit**

```bash
mkdir -p src/tenortui/styles
git add src/tenortui/styles/
git commit -m "feat: add Textual CSS stylesheet"
```

---

### Task 13: Main App & Entry Point

**Files:**
- Create: `src/tenortui/app.py`

- [ ] **Step 1: Implement the main Textual App**

Create `src/tenortui/app.py`:

```python
import argparse
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import LoadingIndicator

from tenortui.config import load_config
from tenortui.exceptions import ConfigError, ProviderError, SymbolNotFoundError
from tenortui.providers import PROVIDERS
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


class TenorTUI(App):
    CSS_PATH = "styles/app.tcss"
    TITLE = "TenorTUI"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("slash", "focus_search", "Search"),
        ("s", "focus_search", "Search"),
        ("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, provider):
        super().__init__()
        self._provider = provider
        self._current_symbol: str | None = None
        self._current_expiration: str | None = None
        self._current_price: float | None = None

    def compose(self) -> ComposeResult:
        yield TickerBar()
        with Vertical(id="main-content"):
            yield ExpirySelector()
            yield ChainTable()
        yield StatusBar(provider_name=self._provider.name)

    def on_mount(self) -> None:
        self.query_one(TickerBar).focus_input()

    def on_ticker_bar_ticker_submitted(self, event: TickerBar.TickerSubmitted) -> None:
        self._current_symbol = event.symbol
        self._load_ticker(event.symbol)

    def on_expiry_selector_expiry_selected(self, event: ExpirySelector.ExpirySelected) -> None:
        self._current_expiration = event.expiration
        if self._current_symbol:
            self._load_chain(self._current_symbol, event.expiration)

    def action_focus_search(self) -> None:
        self.query_one(TickerBar).focus_input()

    def action_refresh(self) -> None:
        if self._current_symbol:
            self._load_ticker(self._current_symbol)

    @work(exclusive=True, thread=True)
    def _load_ticker(self, symbol: str) -> None:
        ticker_bar = self.query_one(TickerBar)
        expiry_selector = self.query_one(ExpirySelector)
        chain_table = self.query_one(ChainTable)

        self.call_from_thread(setattr, chain_table, "loading", True)

        try:
            quote = self._provider.get_quote(symbol)
            self._current_price = quote.price
            self.call_from_thread(ticker_bar.show_quote, quote)
        except SymbolNotFoundError:
            self.call_from_thread(ticker_bar.show_error, f"Symbol '{symbol}' not found")
            return
        except ProviderError as e:
            self.call_from_thread(ticker_bar.show_error, str(e))
            return

        try:
            expirations = self._provider.get_expirations(symbol)
            self.call_from_thread(expiry_selector.set_expirations, expirations)

            if expirations:
                self._current_expiration = expirations[0]
                chain = self._provider.get_chain(symbol, expirations[0])
                self.call_from_thread(chain_table.display_chain, chain, self._current_price)
            else:
                self.call_from_thread(
                    chain_table.show_message,
                    f"No options available for {symbol}",
                )
        except ProviderError as e:
            self.call_from_thread(chain_table.show_message, str(e))

        self.call_from_thread(setattr, chain_table, "loading", False)
        status_bar = self.query_one(StatusBar)
        self.call_from_thread(status_bar.update_refresh_time)

    @work(exclusive=True, thread=True, group="chain")
    def _load_chain(self, symbol: str, expiration: str) -> None:
        chain_table = self.query_one(ChainTable)

        self.call_from_thread(setattr, chain_table, "loading", True)

        try:
            chain = self._provider.get_chain(symbol, expiration)
            self.call_from_thread(chain_table.display_chain, chain, self._current_price)
        except ProviderError as e:
            self.call_from_thread(chain_table.show_message, str(e))

        self.call_from_thread(setattr, chain_table, "loading", False)
        status_bar = self.query_one(StatusBar)
        self.call_from_thread(status_bar.update_refresh_time)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tenortui",
        description="Terminal UI for browsing stock options chains",
        epilog="Provider config in ~/.tenorrc:\n  yahoo: no config needed\n  tradier: requires 'api_key', optional 'sandbox' (default: false)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        default=None,
        help="Data provider to use (overrides ~/.tenorrc)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        config = load_config(provider_override=args.provider)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    provider_cls = PROVIDERS[config.provider_name]

    if config.provider_name == "tradier":
        provider = provider_cls(
            api_key=config.provider_config["api_key"],
            sandbox=config.provider_config.get("sandbox", False),
        )
    else:
        provider = provider_cls()

    app = TenorTUI(provider=provider)
    app.run()
```

- [ ] **Step 2: Verify the app launches**

Run: `cd /Users/jravaliya/Code/tenor-tui && source .venv/bin/activate && tenortui`
Expected: TUI launches with empty state, ticker input focused, status bar showing "yahoo". Press `q` to quit.

- [ ] **Step 3: Commit**

```bash
git add src/tenortui/app.py
git commit -m "feat: add main TenorTUI app with keybindings and worker dispatch"
```

---

### Task 14: Integration Tests

**Files:**
- Create: `tests/test_app.py`

- [ ] **Step 1: Write integration tests using Textual Pilot**

Create `tests/test_app.py`:

```python
import pytest
from unittest.mock import patch

from tenortui.app import TenorTUI


@pytest.fixture
def app(fake_provider):
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_app_launches(app):
    async with app.run_test() as pilot:
        assert app.title == "TenorTUI"


@pytest.mark.asyncio
async def test_search_ticker(app):
    async with app.run_test() as pilot:
        # Type ticker in the input
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        # Wait for threaded worker to complete
        await app.workers.wait_for_complete()

        # Quote should be displayed
        from tenortui.widgets.ticker_bar import TickerBar
        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered or "213.25" in rendered


@pytest.mark.asyncio
async def test_focus_search(app):
    async with app.run_test() as pilot:
        await pilot.press("slash")
        from tenortui.widgets.ticker_bar import TickerBar
        input_widget = app.query_one(TickerBar).query_one("#ticker-input")
        assert input_widget.has_focus
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_app.py
git commit -m "feat: add integration tests with Textual Pilot"
```

---

### Task 15: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md`:

```markdown
# TenorTUI

A terminal UI for browsing stock options chains with pluggable data providers.

## Install

```bash
pip install .
```

## Usage

```bash
tenortui                    # Uses Yahoo Finance (default, no config needed)
tenortui --provider tradier # Use Tradier (requires API key in ~/.tenorrc)
```

## Configuration

Create `~/.tenorrc` (optional):

```yaml
---
default: yahoo

yahoo: {}

tradier:
  api_key: your-api-key-here
  sandbox: false
```

## Keybindings

| Key | Action |
|-----|--------|
| `/` or `s` | Focus search |
| `Enter` | Search ticker |
| `Ctrl+R` | Refresh data |
| `Left/Right` | Switch expiration |
| `Tab` | Cycle calls/puts |
| `q` | Quit |

## Data Providers

| Provider | API Key Required | Greeks |
|----------|-----------------|--------|
| Yahoo Finance | No | No |
| Tradier | Yes | Yes |

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with install, usage, and keybindings"
```

---

### Task 16: Manual Smoke Test

- [ ] **Step 1: Run the app and test with a real ticker**

Run: `cd /Users/jravaliya/Code/tenor-tui && source .venv/bin/activate && tenortui`

Test the following:
1. Type `AAPL` and press Enter — should load quote and expiration tabs
2. Click or arrow to a different expiration — should load that chain
3. Press `Ctrl+R` — should refresh the data
4. Press `/` — should focus the search input
5. Type `FAKESYMBOL` and press Enter — should show error
6. Press `q` — should quit

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Fix any issues found during smoke test**

Address any layout, data mapping, or interaction issues discovered.

- [ ] **Step 4: Final commit if fixes were needed**

```bash
git add -A
git commit -m "fix: address issues from smoke testing"
```
