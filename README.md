# TenorTUI

A terminal UI for browsing stock options chains — built for your data source, navigated with your vim muscle memory.

TenorTUI is a data-source agnostic options chain viewer for the terminal. Plug in a provider and the UI adapts to what it offers: basic quotes with Yahoo Finance, full Greeks with Tradier, or your own custom provider. Navigation is vim-native throughout — `j`/`k` to scroll, `h`/`l` to switch panes, `g`/`G` to jump, `:` for the command palette.

## Features

- **Pluggable data providers** — Yahoo Finance out of the box (no config), Tradier for Greeks, or implement your own
- **Vim-style navigation** — `j`/`k`/`g`/`G`/`h`/`l` plus a `:` command palette
- **ATM strike detection** — automatically finds the at-the-money strike and centers it in the viewport
- **Recently viewed tickers** — quick access to your last 10 symbols with live quotes on launch

## Quick Start

**Prerequisites:** Python 3.11+, git

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
pip install .
tenortui
```

Yahoo Finance is the default provider and requires zero configuration.

## Configuration

TenorTUI looks for a config file at `~/.config/tenor/config.yaml` (falls back to `~/.tenorrc`).

Configuration is **optional** — Yahoo Finance works without it. You only need a config file to use Tradier or change the default provider.

```yaml
---
# Which provider to use by default
default: yahoo

# Yahoo Finance — no configuration needed
yahoo: {}

# Tradier — requires an API key from developer.tradier.com
tradier:
  api_key: your-api-key-here
  sandbox: false   # set to true to use the sandbox API
```

### Yahoo Finance

No setup required. Provides quotes and options chains without Greeks.

### Tradier

1. Get an API key from [developer.tradier.com](https://developer.tradier.com)
2. Add it to your config file (see example above)
3. Run with `tenortui --provider tradier` or set `default: tradier` in your config

Tradier provides full options data including Greeks (delta, gamma, theta, vega, rho). Greek columns appear automatically when available.

### CLI Override

Override the config file provider for a single session:

```bash
tenortui --provider tradier
```

## Keybindings

Press `?` at any time to see the help overlay.

### Navigation

| Key | Action |
|-----|--------|
| `j` / `k` | Move down / up in lists and tables |
| `h` / `l` | Switch to previous / next pane |
| `g` | Jump to top of list |
| `G` | Jump to bottom of list |
| `Tab` / `Shift+Tab` | Next / previous pane |

### Actions

| Key | Action |
|-----|--------|
| `/` or `s` | Focus search bar |
| `r` | Refresh current data |
| `Enter` | Select / expand |
| `q` | Quit |

### Panels

| Key | Action |
|-----|--------|
| `?` | Toggle help overlay |
| `:` | Open command palette |

### Command Palette

Press `:` to open the command palette, then type a command:

| Command | Action |
|---------|--------|
| `:quit` | Exit the app |
| `:search AAPL` | Search for a ticker |
| `:help` | Show help overlay |

## Data Providers

| Provider | Auth Required | Greeks |
|----------|--------------|--------|
| Yahoo Finance | No | No |
| Tradier | Yes (API key) | Yes |

### Adding Your Own Provider

Providers implement the `DataProvider` protocol defined in `src/tenortui/providers/base.py`:

```python
class DataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
```

Implement these three methods, register your provider in `src/tenortui/providers/__init__.py`, and it's ready to use. Provider methods are synchronous — the app wraps them with `asyncio.to_thread()` to keep the UI responsive.

## Development

### Setup

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Commands

```bash
# Run the app
tenortui

# Run all tests
python -m pytest -v

# Run a single test
python -m pytest tests/test_models.py::test_mid_price -v

# Lint
ruff check src/ tests/

# Format (add --fix to auto-format)
ruff format --check src/ tests/
```

### Architecture

TenorTUI is built with [Textual](https://textual.textualize.io/), a modern Python TUI framework.

**App flow:** On launch, recently viewed tickers are shown with live quotes. Selecting or searching a ticker fetches its quote and expiration dates, then loads the options chain for the nearest expiry. Switching expiry tabs loads a new chain.

**Widget hierarchy:**
- `TickerBar` — search input + quote display
- `RecentlyViewed` — recently viewed tickers with live prices
- `ExpirySelector` — tabbed expiration date selector
- `ChainTable` — calls and puts tables with ATM divider
- `StatusBar` — provider name and last refresh time
- `CommandPalette` — vim-style `:` command input

**Provider pattern:** Data providers are synchronous classes behind a Protocol interface. The app wraps all provider calls with `asyncio.to_thread()` so the UI stays responsive during network requests.

**Config:** YAML config at `~/.config/tenor/config.yaml`. History stored at `~/.config/tenor/history.json` (last 10 tickers).

See `CLAUDE.md` for the full development reference.

## Built with Claude

TenorTUI is a Claude-first project. Development is driven by [Claude Code](https://claude.ai/code), with structured workflows that enable parallel development across multiple features simultaneously.

**How it works:**
- Every change follows: GitHub Issue → git worktree → branch → PR → merge
- Multiple Claude instances work on separate features in isolated worktrees
- `CLAUDE.md` is the canonical development guide — it contains everything needed to understand the codebase, run tests, and follow the contribution workflow

Contributions are welcome — both human and AI-assisted. Check the [GitHub Issues](https://github.com/jayrav13/tenor-tui/issues) for open tasks, and see `CLAUDE.md` for the full development workflow.
