# TenorTUI Design Spec

**Date:** 2026-03-19

## Overview

A standalone Python TUI for browsing stock options chains. Invoked as `tenortui`, configured via `~/.tenorrc` (YAML). Supports pluggable data sources (Yahoo Finance, Tradier) behind a provider abstraction. No database dependency — hits APIs directly.

## Project Structure

```
tenor-tui/
├── pyproject.toml
├── README.md
├── src/
│   └── tenortui/
│       ├── __init__.py
│       ├── app.py              # Textual App class, main entry point
│       ├── config.py           # ~/.tenorrc parsing, provider selection
│       ├── exceptions.py       # ProviderError, SymbolNotFoundError, ConfigError
│       ├── models.py           # Dataclasses: Quote, OptionContract, OptionsChain
│       ├── providers/
│       │   ├── __init__.py     # PROVIDERS registry dict
│       │   ├── base.py         # DataProvider Protocol
│       │   ├── yahoo.py        # Yahoo Finance via yfinance
│       │   └── tradier.py      # Tradier via requests
│       ├── widgets/
│       │   ├── __init__.py
│       │   ├── ticker_bar.py   # Search input + quote display
│       │   ├── expiry_selector.py  # Expiration date tabs
│       │   ├── chain_table.py  # Options chain DataTable
│       │   └── status_bar.py   # Provider name, keybindings, last refresh
│       └── styles/
│           └── app.tcss        # Textual CSS
└── tests/
```

**Entry point:** `[project.scripts] tenortui = "tenortui.app:main"` in `pyproject.toml`.

**Python version:** 3.11+

**Dependencies:**
- `textual` — TUI framework
- `yfinance` — Yahoo provider
- `requests` — Tradier provider HTTP client
- `pyyaml` — config parsing

## Data Models

```python
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
    option_type: str          # "call" or "put"
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

@dataclass
class OptionsChain:
    symbol: str
    expiration: str           # ISO date string
    calls: list[OptionContract]
    puts: list[OptionContract]
```

## Provider Interface

```python
class DataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
```

Three methods. Each provider maps its API response into the shared dataclasses. The TUI never sees raw API data.

All provider methods are synchronous. The App and widgets must call them via `self.run_worker()` (Textual's thread-pool worker) to avoid blocking the event loop. Workers should use `exclusive=True` to cancel stale requests when a new ticker or expiration is selected.

### Provider Registry

```python
PROVIDERS = {
    "yahoo": YahooProvider,
    "tradier": TradierProvider,
}
```

Adding a new provider = write the class, add it to the dict.

### Yahoo Provider

- Uses `yfinance.Ticker` for quote, expirations, and chain data
- No auth required
- Does NOT return greeks — greek columns are `None`, UI hides greek columns when all values are `None`

### Tradier Provider

- Uses `requests` against `https://api.tradier.com/v1/` (or `https://sandbox.tradier.com/v1/` when `sandbox: true`)
- Auth: `Authorization: Bearer {api_key}` header
- Endpoints: `/markets/quotes`, `/markets/options/expirations`, `/markets/options/chains?greeks=true`
- Returns greeks natively (delta, gamma, theta, vega, rho)

## Configuration

**File:** `~/.tenorrc` (YAML)

```yaml
---
default: yahoo

yahoo: {}

tradier:
  api_key: your-api-key-here
  sandbox: false
```

**Rules:**
- `default` key selects the active provider. If omitted, uses the first provider key with valid config.
- `yahoo` needs no credentials. Empty dict or omit entirely.
- `tradier` requires `api_key`. `sandbox` defaults to `false`.
- No `~/.tenorrc` at all: defaults to Yahoo silently. Zero config to get started.
- Bad YAML, missing required fields, unknown provider: clear stderr message, exit code 1.

**CLI flags:**
- `tenortui` — uses config / defaults
- `tenortui --provider yahoo` — override provider for this session
- `tenortui --help` — shows available providers and required config fields

## UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Search: AAPL | Apple Inc.  $213.25  +1.42 (+0.67%)         │
├──────────────────────────────────────────────────────────────┤
│  Mar 21 | Mar 28 | Apr 04 | Apr 17 | May 16 | Jun 20 | ... │
├──────────────────────────────────────────────────────────────┤
│                          CALLS                               │
│ Strike |  Bid  |  Ask  |  Mid  |  Vol  |   OI  |  IV   | D  │
│ 200.00 | 14.20 | 14.50 | 14.35 |  1234 |  8901 | 0.32  |.81 │
│ 205.00 | 10.10 | 10.40 | 10.25 |   892 |  5432 | 0.29  |.68 │
│ ─ ─ ─ ATM ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
│ 215.00 |  3.40 |  3.60 |  3.50 |  3456 | 15678 | 0.25  |.38 │
│ 220.00 |  1.50 |  1.65 |  1.58 |  1876 |  9012 | 0.24  |.22 │
├──────────────────────────────────────────────────────────────┤
│                          PUTS                                │
│ Strike |  Bid  |  Ask  |  Mid  |  Vol  |   OI  |  IV   | D  │
│ 200.00 |  0.85 |  0.95 |  0.90 |   567 |  3456 | 0.28  |-.18│
│ 205.00 |  1.90 |  2.10 |  2.00 |   743 |  4567 | 0.26  |-.31│
├──────────────────────────────────────────────────────────────┤
│  yahoo | Ctrl+R: Refresh | /: Search | Last: 14:32:05       │
└──────────────────────────────────────────────────────────────┘
```

**Components:**
1. **Ticker Bar** — input field + quote display. Type ticker, press Enter to search.
2. **Expiry Selector** — horizontal tab strip. Left/Right arrows or click to switch. Fetches chain on selection.
3. **Chain Table** — two DataTable widgets (calls then puts). Scrollable. ATM divider inserted above the first strike greater than the current quote price; if no quote is available, no divider is shown. Greek columns shown only when provider supplies them.
4. **Status Bar** — active provider, keybinding hints, last fetch timestamp.

**Keybindings:**
- `/` or `s` — focus search input
- `Ctrl+R` — refresh current ticker + expiration
- `Left/Right` — switch expiration tabs
- `q` — quit
- `Tab` — cycle between calls and puts tables

**Search behavior:**
1. User types ticker, presses Enter
2. Fetch quote + expirations (can be parallel via Textual workers)
3. Display quote in ticker bar, populate expiry tabs
4. Auto-select nearest expiration, fetch that chain
5. On expiry tab change, fetch and display that chain

**Loading state:** spinner overlay on chain table area while fetching (Textual built-in `Loading` indicator).

## Exceptions

Defined in `exceptions.py`:

```python
class ProviderError(Exception):
    """Base exception for all provider errors."""

class SymbolNotFoundError(ProviderError):
    """Raised when a ticker symbol is not recognized by the provider."""

class ConfigError(Exception):
    """Raised for config file parsing or validation errors."""
```

Providers catch API-specific errors and raise `ProviderError` or `SymbolNotFoundError`. Config parsing raises `ConfigError`.

## Error Handling

- **Invalid ticker:** `SymbolNotFoundError`. Inline error in ticker bar. Previous ticker stays loaded.
- **Network errors / timeouts:** Caught at provider level, re-raised as `ProviderError`. Error shown in status bar. Previous data stays visible.
- **No options available:** Empty expiration list. "No options available for {symbol}" shown in chain area.
- **Missing data in response:** Defaults — `0` for volume/OI, `0.0` for bid/ask, `None` for greeks.
- **Config errors:** Clear stderr message, exit code 1. No TUI rendered.
- **No `~/.tenorrc`:** Not an error. Yahoo default, app starts normally.

## Testing

- **Provider unit tests** — mock HTTP responses (use `unittest.mock.patch` on `yfinance` / `requests`). Each provider gets tests for `get_quote`, `get_expirations`, `get_chain` with sample API responses as fixtures.
- **Config parsing tests** — valid YAML, missing file (defaults to Yahoo), malformed YAML (raises `ConfigError`), missing required fields (e.g., Tradier without `api_key`), `--provider` CLI override.
- **Model tests** — `OptionContract.mid` property returns `(bid + ask) / 2`, default values for missing data fields.
- **Widget integration tests** — use Textual's `App.run_test()` / `Pilot` API. Test search flow (type ticker, press Enter, verify quote appears), expiry tab switching, error display on invalid ticker.
- **Test fixtures** — sample JSON responses from Yahoo and Tradier stored in `tests/fixtures/`.

## Design Decisions

1. **Provider abstraction** — `DataProvider` Protocol with three methods. One provider active at a time. Clean separation, easy to extend.
2. **`requests` over `httpx`** — simpler, no async needed. Textual's `run_worker()` handles threading.
3. **Mid price as `@property`** — `OptionContract.mid` is a computed `@property` returning `(bid + ask) / 2`. Not stored, not sourced. Consistent across providers.
4. **Greek columns conditional** — shown only when provider returns them. Yahoo: hidden. Tradier: visible.
5. **Zero-config default** — Yahoo requires no API key. App works immediately with no `~/.tenorrc`.
6. **On-demand fetch only** — no auto-refresh. Ctrl+R to reload. Avoids rate limit complexity.
7. **Dependency version bounds** — `pyproject.toml` specifies lower bounds (e.g., `textual>=0.50`, `yfinance>=0.2.30`). No lockfile initially; add one if reproducibility becomes an issue.
