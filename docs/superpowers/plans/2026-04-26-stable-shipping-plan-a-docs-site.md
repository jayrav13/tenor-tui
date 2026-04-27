# Stable Shipping — Plan A: Docs Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a MkDocs Material docs site for TenorTUI, deployed to GitHub Pages at `jayravaliya.com/tenor-tui/`, with deterministic SVG snapshots and VHS-generated GIFs driven from a `FixtureProvider`.

**Architecture:** A new `FixtureProvider` (implementing the existing `DataProvider` protocol) returns frozen, predictable data so screenshots/demos regenerate identically. A Python script (`bin/snapshot`) drives the Textual app via the `Pilot` API and writes SVGs via `app.export_screenshot()`. VHS `.tape` files invoke `tenortui --provider fixture` to produce GIFs. The MkDocs Material site under `docs/site/` references those assets. A new `docs.yml` workflow deploys to the `gh-pages` branch on merge to `main`; a new `docs-build` CI job runs `mkdocs build --strict` on PRs to catch broken links.

**Tech Stack:** Python 3.11+, Textual (existing), MkDocs Material, VHS (charmbracelet), Poetry, GitHub Actions.

**Spec reference:** `docs/superpowers/specs/2026-04-26-stable-product-shipping-design.md` — Plan A covers components 4 (docs site) plus the FixtureProvider/snapshot tooling. Components 1–3, 5, 6 (PyPI distribution, README rewrite, CLAUDE.md docs sync, 1.0.0 bump) are deferred to Plan B.

**Out of scope for Plan A:**
- `LICENSE` file (Plan B)
- `CHANGELOG.md` (Plan B)
- `pyproject.toml` PyPI metadata changes (Plan B)
- `release.yml` workflow (Plan B)
- README rewrite (Plan B)
- CLAUDE.md docs sync table (Plan B)
- Bumping the version (stays at 0.1.0)

---

## File Structure

**Create:**
- `src/tenortui/providers/fixture.py` — `FixtureProvider` class with deterministic data
- `tests/test_fixture_provider.py` — unit tests for `FixtureProvider`
- `bin/snapshot` — executable Python script that drives the Textual app and writes SVGs
- `tests/test_snapshot_script.py` — smoke test that `bin/snapshot --list` exits 0
- `Makefile` — `make snapshots`, `make demos`, `make docs`, `make docs-serve` targets
- `docs/tapes/_common.tape` — shared VHS prelude (font, dimensions)
- `docs/tapes/launch-and-search.tape`
- `docs/tapes/watchlist-flow.tape`
- `docs/tapes/expiry-and-greeks.tape`
- `docs/site/mkdocs.yml`
- `docs/site/docs/index.md`
- `docs/site/docs/installation.md`
- `docs/site/docs/quickstart.md`
- `docs/site/docs/configuration.md`
- `docs/site/docs/contributing.md`
- `docs/site/docs/features/options-chain.md`
- `docs/site/docs/features/watchlists.md`
- `docs/site/docs/features/providers.md`
- `docs/site/docs/features/keybindings.md`
- `docs/site/docs/assets/snapshots/*.svg` — generated, committed
- `docs/site/docs/assets/demos/*.gif` — generated, committed
- `.github/workflows/docs.yml` — deploy to gh-pages on merge to main

**Modify:**
- `src/tenortui/providers/__init__.py` — register `FixtureProvider` in `PROVIDERS` dict
- `pyproject.toml` — add `[tool.poetry.group.docs]` with `mkdocs-material`
- `.github/workflows/ci.yml` — add `docs-build` job
- `.gitignore` — no change (assets are committed)

---

## Task 1: Create the FixtureProvider

**Files:**
- Create: `src/tenortui/providers/fixture.py`
- Test: `tests/test_fixture_provider.py`

**Why:** Snapshots and tapes need deterministic data. Live providers (Yahoo, Tradier) change between runs, which would churn SVGs/GIFs on every regeneration.

**Design:** `FixtureProvider` implements the `DataProvider` protocol (`src/tenortui/providers/base.py`). Returns a fixed quote, fixed expiration list, and a fixed options chain for any symbol. Pre-baked data covers AAPL specifically (the symbol used in demos); other symbols return a generic placeholder so the app doesn't crash if a user tries `--provider fixture` with another ticker.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fixture_provider.py
import pytest

from tenortui.providers.fixture import FixtureProvider


def test_name_attribute():
    provider = FixtureProvider()
    assert provider.name == "fixture"


def test_get_quote_aapl_is_deterministic():
    p1 = FixtureProvider().get_quote("AAPL")
    p2 = FixtureProvider().get_quote("AAPL")
    assert p1.symbol == "AAPL"
    assert p1.name == "Apple Inc."
    assert p1.price == p2.price
    assert p1.change == p2.change
    assert p1.volume == p2.volume


def test_get_quote_unknown_symbol_returns_generic():
    quote = FixtureProvider().get_quote("ZZZZ")
    assert quote.symbol == "ZZZZ"
    assert quote.price > 0


def test_get_expirations_aapl_returns_three_dates():
    expirations = FixtureProvider().get_expirations("AAPL")
    assert len(expirations) == 3
    # Returns sorted chronologically
    assert expirations == sorted(expirations)


def test_get_chain_returns_calls_and_puts():
    chain = FixtureProvider().get_chain("AAPL", "2026-05-15")
    assert chain.symbol == "AAPL"
    assert chain.expiration == "2026-05-15"
    assert len(chain.calls) > 0
    assert len(chain.puts) > 0
    # All calls have option_type set correctly
    assert all(c.option_type == "call" for c in chain.calls)
    assert all(p.option_type == "put" for p in chain.puts)


def test_get_chain_includes_atm_strike():
    quote = FixtureProvider().get_quote("AAPL")
    chain = FixtureProvider().get_chain("AAPL", "2026-05-15")
    strikes = [c.strike for c in chain.calls]
    # The ATM strike should be near the underlying price
    assert min(strikes) <= quote.price <= max(strikes)


def test_get_chain_unknown_expiration_raises():
    with pytest.raises(ValueError):
        FixtureProvider().get_chain("AAPL", "1999-01-01")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_fixture_provider.py -v`
Expected: All 7 tests FAIL with `ModuleNotFoundError: No module named 'tenortui.providers.fixture'`.

- [ ] **Step 3: Implement FixtureProvider**

Create `src/tenortui/providers/fixture.py`:

```python
"""Deterministic provider for screenshots, demos, and snapshot tests.

Returns frozen data so SVGs and GIFs regenerate identically across runs.
"""

from tenortui.models import OptionContract, OptionsChain, Quote


_AAPL_QUOTE = Quote(
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
    earnings_date="May 1",
    moving_avg_50d=208.40,
    moving_avg_200d=196.80,
)

_AAPL_EXPIRATIONS = ["2026-05-15", "2026-06-19", "2026-07-17"]


def _aapl_chain(expiration: str) -> OptionsChain:
    """Generate a deterministic options chain centered around 213.25."""
    strikes = [200.0, 205.0, 210.0, 215.0, 220.0, 225.0, 230.0]
    calls = []
    puts = []
    for strike in strikes:
        # Simple deterministic pricing — not realistic, just stable
        moneyness = 213.25 - strike
        call_intrinsic = max(0.0, moneyness)
        put_intrinsic = max(0.0, -moneyness)
        call_price = round(call_intrinsic + 5.0, 2)
        put_price = round(put_intrinsic + 5.0, 2)
        contract_date = expiration.replace("-", "")[2:]
        strike_padded = f"{int(strike * 1000):08d}"
        calls.append(
            OptionContract(
                contract_symbol=f"AAPL{contract_date}C{strike_padded}",
                option_type="call",
                strike=strike,
                bid=round(call_price - 0.10, 2),
                ask=round(call_price + 0.10, 2),
                last_price=call_price,
                volume=int(strike * 10),
                open_interest=int(strike * 50),
                implied_volatility=0.30 + (strike - 215.0) * 0.005,
                delta=None,
                gamma=None,
                theta=None,
                vega=None,
                rho=None,
            )
        )
        puts.append(
            OptionContract(
                contract_symbol=f"AAPL{contract_date}P{strike_padded}",
                option_type="put",
                strike=strike,
                bid=round(put_price - 0.10, 2),
                ask=round(put_price + 0.10, 2),
                last_price=put_price,
                volume=int(strike * 8),
                open_interest=int(strike * 40),
                implied_volatility=0.32 + (215.0 - strike) * 0.005,
                delta=None,
                gamma=None,
                theta=None,
                vega=None,
                rho=None,
            )
        )
    return OptionsChain(symbol="AAPL", expiration=expiration, calls=calls, puts=puts)


class FixtureProvider:
    """Deterministic provider for screenshots and demos."""

    name = "fixture"

    def get_quote(self, symbol: str) -> Quote:
        if symbol.upper() == "AAPL":
            return _AAPL_QUOTE
        # Generic placeholder so the app doesn't crash on other symbols
        return Quote(
            symbol=symbol.upper(),
            name=f"{symbol.upper()} Demo Inc.",
            price=100.00,
            change=0.50,
            change_percent=0.50,
            volume=1_000_000,
            market_cap=10_000_000_000,
        )

    def get_expirations(self, symbol: str) -> list[str]:
        if symbol.upper() == "AAPL":
            return _AAPL_EXPIRATIONS
        return ["2026-05-15"]

    def get_chain(self, symbol: str, expiration: str) -> OptionsChain:
        if symbol.upper() == "AAPL":
            if expiration not in _AAPL_EXPIRATIONS:
                raise ValueError(
                    f"Unknown expiration {expiration!r}; "
                    f"valid: {_AAPL_EXPIRATIONS}"
                )
            return _aapl_chain(expiration)
        # Generic single-strike chain for other symbols
        if expiration != "2026-05-15":
            raise ValueError(f"Unknown expiration {expiration!r} for {symbol}")
        return OptionsChain(
            symbol=symbol.upper(),
            expiration=expiration,
            calls=[
                OptionContract(
                    contract_symbol=f"{symbol.upper()}260515C00100000",
                    option_type="call",
                    strike=100.0,
                    bid=4.90,
                    ask=5.10,
                    last_price=5.00,
                    volume=100,
                    open_interest=500,
                    implied_volatility=0.30,
                    delta=None,
                    gamma=None,
                    theta=None,
                    vega=None,
                    rho=None,
                )
            ],
            puts=[
                OptionContract(
                    contract_symbol=f"{symbol.upper()}260515P00100000",
                    option_type="put",
                    strike=100.0,
                    bid=4.90,
                    ask=5.10,
                    last_price=5.00,
                    volume=100,
                    open_interest=500,
                    implied_volatility=0.30,
                    delta=None,
                    gamma=None,
                    theta=None,
                    vega=None,
                    rho=None,
                )
            ],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_fixture_provider.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Run lint check**

Run: `poetry run ruff check src/tenortui/providers/fixture.py tests/test_fixture_provider.py`
Expected: PASS (no errors).

If errors appear, fix them and re-run.

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/providers/fixture.py tests/test_fixture_provider.py
git commit -m "$(cat <<'EOF'
feat: add FixtureProvider for deterministic screenshots

FixtureProvider implements the DataProvider protocol with frozen,
predictable data so screenshots and VHS demos regenerate identically.
Pre-baked data for AAPL; generic placeholder for other symbols.

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Register FixtureProvider in providers registry

**Files:**
- Modify: `src/tenortui/providers/__init__.py`

**Why:** The CLI flag `--provider fixture` needs the provider to be in the `PROVIDERS` dict.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_fixture_provider.py`:

```python
def test_fixture_provider_registered():
    from tenortui.providers import PROVIDERS
    from tenortui.providers.fixture import FixtureProvider

    assert "fixture" in PROVIDERS
    assert PROVIDERS["fixture"] is FixtureProvider
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run python -m pytest tests/test_fixture_provider.py::test_fixture_provider_registered -v`
Expected: FAIL with `assert "fixture" in {"yahoo": ..., "tradier": ...}`.

- [ ] **Step 3: Update the registry**

Edit `src/tenortui/providers/__init__.py` to:

```python
from tenortui.providers.base import DataProvider as DataProvider
from tenortui.providers.fixture import FixtureProvider
from tenortui.providers.yahoo import YahooProvider
from tenortui.providers.tradier import TradierProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
    "tradier": TradierProvider,
    "fixture": FixtureProvider,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run python -m pytest tests/test_fixture_provider.py::test_fixture_provider_registered -v`
Expected: PASS.

- [ ] **Step 5: Verify CLI works**

Run: `poetry run tenortui --provider fixture` (then immediately Ctrl+C after the UI loads).
Expected: TenorTUI launches without errors. Search bar is visible. Status bar shows `Provider: fixture`.

- [ ] **Step 6: Run full test suite to confirm no regressions**

Run: `poetry run python -m pytest`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/providers/__init__.py tests/test_fixture_provider.py
git commit -m "$(cat <<'EOF'
feat: register FixtureProvider, enable --provider fixture

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add MkDocs dependencies via Poetry docs group

**Files:**
- Modify: `pyproject.toml`
- Modify: `poetry.lock` (regenerated)

**Why:** Docs site building needs `mkdocs-material`. Adding it as a Poetry group keeps it out of regular installs but makes it reproducible for the docs CI job.

- [ ] **Step 1: Add the docs group to pyproject.toml**

Add this block to `pyproject.toml` after the existing `[tool.poetry.group.dev.dependencies]` block:

```toml
[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs-material = ">=9.5"
```

The `optional = true` flag means `poetry install` (without args) won't pull these in; only `poetry install --with docs` does.

- [ ] **Step 2: Lock dependencies**

Run: `poetry lock --no-update`
Expected: `poetry.lock` updates with the new packages. No errors.

If `poetry lock --no-update` complains, run `poetry lock` (without `--no-update`).

- [ ] **Step 3: Install with docs group**

Run: `poetry install --with docs`
Expected: New packages install (mkdocs, mkdocs-material, and dependencies). No errors.

- [ ] **Step 4: Verify mkdocs is on PATH**

Run: `poetry run mkdocs --version`
Expected: Prints something like `mkdocs, version 1.6.x`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "$(cat <<'EOF'
chore: add mkdocs-material as optional poetry docs group

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Create the snapshot script (single hero snapshot)

**Files:**
- Create: `bin/snapshot`
- Test: `tests/test_snapshot_script.py`

**Why:** Generates SVG screenshots of the TUI by driving the Textual app via the `Pilot` API and calling `app.export_screenshot()`. Starts with one snapshot (the chain-loaded "hero" view) to validate the approach end-to-end before adding more.

**Design:** `bin/snapshot` is an executable Python script. When run with no args, it generates all snapshots. With `--list`, it lists snapshot names without generating. Snapshots are async functions registered in a dict; each function takes a `Pilot` and returns the SVG content. Output goes to `docs/site/docs/assets/snapshots/<name>.svg`.

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_snapshot_script.py
import subprocess
import sys


def test_snapshot_script_list_exits_zero():
    """The snapshot script should accept --list and exit 0."""
    result = subprocess.run(
        [sys.executable, "bin/snapshot", "--list"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "hero" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run python -m pytest tests/test_snapshot_script.py -v`
Expected: FAIL with `FileNotFoundError` or non-zero exit.

- [ ] **Step 3: Create the snapshot script**

Create `bin/snapshot` (must be executable):

```python
#!/usr/bin/env python3
"""Generate SVG snapshots of TenorTUI for the docs site.

Usage:
  bin/snapshot              # generate all snapshots
  bin/snapshot --list       # list snapshot names without generating
  bin/snapshot hero chain   # generate specific snapshots by name
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Awaitable, Callable

# Ensure src/ is on sys.path when running from the repo
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from tenortui.app import TenorTUI  # noqa: E402
from tenortui.providers.fixture import FixtureProvider  # noqa: E402


OUTPUT_DIR = REPO_ROOT / "docs" / "site" / "docs" / "assets" / "snapshots"


SnapshotFn = Callable[["object"], Awaitable[str]]


async def hero(pilot) -> str:
    """Chain table loaded for AAPL — the headline visual."""
    await pilot.press("a", "a", "p", "l", "enter")
    await pilot.pause(delay=1.0)
    return pilot.app.export_screenshot(title="TenorTUI — AAPL options chain")


SNAPSHOTS: dict[str, SnapshotFn] = {
    "hero": hero,
}


async def _run_snapshot(name: str, fn: SnapshotFn) -> Path:
    app = TenorTUI(provider=FixtureProvider())
    async with app.run_test(size=(140, 40)) as pilot:
        svg = await fn(pilot)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.svg"
    path.write_text(svg, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="Snapshot names to generate")
    parser.add_argument("--list", action="store_true", help="List snapshot names")
    args = parser.parse_args()

    if args.list:
        for name in SNAPSHOTS:
            print(name)
        return 0

    targets = args.names or list(SNAPSHOTS.keys())
    unknown = [n for n in targets if n not in SNAPSHOTS]
    if unknown:
        print(f"Unknown snapshot(s): {unknown}", file=sys.stderr)
        print(f"Known: {list(SNAPSHOTS.keys())}", file=sys.stderr)
        return 2

    for name in targets:
        path = asyncio.run(_run_snapshot(name, SNAPSHOTS[name]))
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then make it executable:

```bash
chmod +x bin/snapshot
```

**Constructor signature:** `TenorTUI(provider=...)` is correct — the constructor at `src/tenortui/app.py:55` accepts `provider` and a handful of optional kwargs (`spread_thresholds`, `greeks_config`, `fred_api_key`, `refresh_config`, `app_config`). The snapshot script uses defaults for everything except `provider`, which is the only required arg.

- [ ] **Step 4: Run smoke test to verify it passes**

Run: `poetry run python -m pytest tests/test_snapshot_script.py -v`
Expected: PASS.

- [ ] **Step 5: Generate the hero snapshot**

Run: `poetry run python bin/snapshot hero`
Expected: Prints `wrote .../docs/site/docs/assets/snapshots/hero.svg`. The SVG file exists and is non-empty.

If this step fails because `TenorTUI(provider=...)` doesn't work, adjust the script to match the actual constructor signature and re-run. Do not skip this step — the script must produce a working SVG before continuing.

- [ ] **Step 6: Inspect the SVG**

Run: `wc -l docs/site/docs/assets/snapshots/hero.svg`
Expected: Several hundred lines of SVG. Open in a browser if you want to verify it looks right.

- [ ] **Step 7: Run lint**

Run: `poetry run ruff check bin/snapshot tests/test_snapshot_script.py`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add bin/snapshot tests/test_snapshot_script.py docs/site/docs/assets/snapshots/hero.svg
git commit -m "$(cat <<'EOF'
feat: add snapshot script with hero SVG generation

bin/snapshot drives the Textual app via Pilot and writes SVGs via
app.export_screenshot(). Initial snapshot: AAPL chain loaded.

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add the remaining snapshots

**Files:**
- Modify: `bin/snapshot`
- Create: `docs/site/docs/assets/snapshots/{chain,watchlist-modal,expiry-tabs,quote-bar}.svg`

**Why:** The docs pages reference multiple stills, not just the hero.

- [ ] **Step 1: Add four more snapshot functions**

In `bin/snapshot`, add these functions before the `SNAPSHOTS` dict:

```python
async def chain(pilot) -> str:
    """Same as hero but framed for the options-chain feature page."""
    await pilot.press("a", "a", "p", "l", "enter")
    await pilot.pause(delay=1.0)
    return pilot.app.export_screenshot(title="TenorTUI — Options chain")


async def watchlist_modal(pilot) -> str:
    """Watchlist picker modal open."""
    await pilot.press("a", "a", "p", "l", "enter")
    await pilot.pause(delay=0.8)
    await pilot.press("w")
    await pilot.pause(delay=0.5)
    return pilot.app.export_screenshot(title="TenorTUI — Watchlist picker")


async def expiry_tabs(pilot) -> str:
    """Expiry tabs visible with a different expiry selected."""
    await pilot.press("a", "a", "p", "l", "enter")
    await pilot.pause(delay=1.0)
    await pilot.press("right")  # switch to next expiry tab
    await pilot.pause(delay=0.5)
    return pilot.app.export_screenshot(title="TenorTUI — Expiry tabs")


async def quote_bar(pilot) -> str:
    """Just-loaded ticker showing the quote bar prominently."""
    await pilot.press("a", "a", "p", "l", "enter")
    await pilot.pause(delay=0.5)
    return pilot.app.export_screenshot(title="TenorTUI — Quote bar")
```

Then update the `SNAPSHOTS` dict to:

```python
SNAPSHOTS: dict[str, SnapshotFn] = {
    "hero": hero,
    "chain": chain,
    "watchlist-modal": watchlist_modal,
    "expiry-tabs": expiry_tabs,
    "quote-bar": quote_bar,
}
```

**Notes on key bindings:**

- `w` is wired to `_action_add_to_watchlist` via the app's `on_key` handler (not its `BINDINGS` list) — see `src/tenortui/app.py:324`. It only opens the picker when there's a focusable item or a current symbol, so the snapshot needs to load AAPL first (which the function does).
- Expiry tab navigation: Textual's `TabbedContent` requires the tab list to be focused before `Right`/`Left` cycle tabs. If `Right` doesn't switch tabs, prepend `await pilot.press("tab")` (or `pilot.press("ctrl+right")`, depending on Textual version) to focus the tab strip first. The first snapshot run will reveal this — adjust if needed.

- [ ] **Step 2: List snapshots to verify registration**

Run: `poetry run python bin/snapshot --list`
Expected: Prints `hero`, `chain`, `watchlist-modal`, `expiry-tabs`, `quote-bar` (one per line).

- [ ] **Step 3: Generate all snapshots**

Run: `poetry run python bin/snapshot`
Expected: Five SVG files written to `docs/site/docs/assets/snapshots/`.

If any snapshot fails (Pilot can't find a key binding, app crashes), debug by running individual snapshots: `poetry run python bin/snapshot watchlist-modal`. Adjust the function until it succeeds.

- [ ] **Step 4: Verify all SVGs are non-empty**

Run: `ls -la docs/site/docs/assets/snapshots/`
Expected: Five files, each several KB.

- [ ] **Step 5: Run lint**

Run: `poetry run ruff check bin/snapshot`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/snapshot docs/site/docs/assets/snapshots/
git commit -m "$(cat <<'EOF'
feat: add chain, watchlist-modal, expiry-tabs, quote-bar snapshots

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Add Makefile with build targets

**Files:**
- Create: `Makefile`

**Why:** Single entry points for regenerating assets and serving docs locally. Keeps commands discoverable without memorizing the full command lines.

- [ ] **Step 1: Create the Makefile**

Create `Makefile` at the repo root:

```makefile
.PHONY: snapshots demos docs docs-serve docs-build help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-15s %s\n", $$1, $$2}'

snapshots:  ## Regenerate SVG snapshots from bin/snapshot
	poetry run python bin/snapshot

demos:  ## Regenerate VHS GIFs from docs/tapes/*.tape
	@for tape in docs/tapes/*.tape; do \
		echo "→ vhs $$tape"; \
		vhs $$tape; \
	done

docs:  ## Build the MkDocs site (output to docs/site/site/)
	cd docs/site && poetry run mkdocs build

docs-strict:  ## Build the MkDocs site with --strict (fails on broken links)
	cd docs/site && poetry run mkdocs build --strict

docs-serve:  ## Serve the MkDocs site at http://127.0.0.1:8000
	cd docs/site && poetry run mkdocs serve
```

- [ ] **Step 2: Verify make help works**

Run: `make help`
Expected: Prints the available targets with descriptions.

- [ ] **Step 3: Verify make snapshots works**

Run: `make snapshots`
Expected: Regenerates the SVGs (no diff if nothing changed).

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "$(cat <<'EOF'
chore: add Makefile with snapshots, demos, docs targets

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Install VHS and create the first tape

**Files:**
- Create: `docs/tapes/_common.tape`
- Create: `docs/tapes/launch-and-search.tape`
- Create: `docs/site/docs/assets/demos/launch-and-search.gif`

**Why:** VHS produces GIFs from script files. Standardizing the prelude (font, dimensions) keeps all demo GIFs visually consistent.

- [ ] **Step 1: Install VHS**

Run: `brew install vhs`
Expected: VHS installs.

If you don't use Homebrew, see https://github.com/charmbracelet/vhs#installation for alternatives.

Verify: `vhs --version` prints a version number.

- [ ] **Step 2: Create the shared prelude**

Create `docs/tapes/_common.tape`:

```
# Shared prelude for all TenorTUI VHS tapes.
# Tapes must `Source docs/tapes/_common.tape` at the top.

Set Theme "Catppuccin Mocha"
Set FontSize 14
Set FontFamily "JetBrainsMono Nerd Font"
Set Width 1200
Set Height 700
Set Padding 20
Set TypingSpeed 80ms
Set PlaybackSpeed 1.0
```

- [ ] **Step 3: Create the launch-and-search tape**

Create `docs/tapes/launch-and-search.tape`:

```
Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/launch-and-search.gif

Hide
Type "poetry run tenortui --provider fixture"
Enter
Sleep 2s
Show

Sleep 1s
Type "AAPL"
Sleep 500ms
Enter
Sleep 3s

# Switch expiry tab
Right
Sleep 1500ms
Right
Sleep 1500ms
Left
Sleep 1500ms

# Quit
Ctrl+C
Sleep 500ms
```

- [ ] **Step 4: Generate the GIF**

Run: `vhs docs/tapes/launch-and-search.tape`
Expected: A GIF file appears at `docs/site/docs/assets/demos/launch-and-search.gif`.

If VHS errors on the font, install `JetBrainsMono Nerd Font` (`brew install --cask font-jetbrains-mono-nerd-font`) or change `_common.tape` to a font you have installed. Update the tape and regenerate.

- [ ] **Step 5: Inspect the GIF**

Open the GIF in a viewer (or `open docs/site/docs/assets/demos/launch-and-search.gif`).
Expected: Shows the app launching, AAPL being typed, the chain loading, expiry tabs being switched.

If the timing looks off (text typing too fast, sleeps too short), tune the `Sleep` values in the tape and regenerate.

- [ ] **Step 6: Commit**

```bash
git add docs/tapes/_common.tape docs/tapes/launch-and-search.tape docs/site/docs/assets/demos/launch-and-search.gif
git commit -m "$(cat <<'EOF'
feat: add VHS shared prelude and launch-and-search demo

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Create the remaining VHS tapes

**Files:**
- Create: `docs/tapes/watchlist-flow.tape`
- Create: `docs/tapes/expiry-and-greeks.tape`
- Create: `docs/site/docs/assets/demos/{watchlist-flow,expiry-and-greeks}.gif`

- [ ] **Step 1: Create the watchlist-flow tape**

Create `docs/tapes/watchlist-flow.tape`:

```
Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/watchlist-flow.gif

Hide
Type "poetry run tenortui --provider fixture"
Enter
Sleep 2s
Show

Sleep 1s
Type "AAPL"
Sleep 500ms
Enter
Sleep 2s

# Open watchlist picker
Type "w"
Sleep 2s

# Close picker
Escape
Sleep 1s

Ctrl+C
Sleep 500ms
```

- [ ] **Step 2: Create the expiry-and-greeks tape**

Create `docs/tapes/expiry-and-greeks.tape`:

```
Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/expiry-and-greeks.gif

Hide
Type "poetry run tenortui --provider fixture"
Enter
Sleep 2s
Show

Sleep 1s
Type "AAPL"
Sleep 500ms
Enter
Sleep 2s

# Cycle through expiries
Right
Sleep 1500ms
Right
Sleep 1500ms
Left
Sleep 1500ms

# Scroll the chain
Down
Down
Down
Down
Sleep 2s
Up
Up
Sleep 2s

Ctrl+C
Sleep 500ms
```

- [ ] **Step 3: Generate both GIFs**

Run: `make demos`
Expected: All three GIFs (re-)generated. No errors.

- [ ] **Step 4: Inspect the GIFs**

Open each GIF and verify the flow looks right.
- `watchlist-flow.gif` — shows AAPL load, watchlist picker open, picker close
- `expiry-and-greeks.gif` — shows expiry tab switching and chain scrolling

Tune `Sleep` values and regenerate as needed.

- [ ] **Step 5: Commit**

```bash
git add docs/tapes/ docs/site/docs/assets/demos/
git commit -m "$(cat <<'EOF'
feat: add watchlist-flow and expiry-and-greeks VHS demos

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Create mkdocs.yml and the index page

**Files:**
- Create: `docs/site/mkdocs.yml`
- Create: `docs/site/docs/index.md`

**Why:** Without `mkdocs.yml` and at least one page, `mkdocs build` fails. This task gets the site building end-to-end with the hero shot.

- [ ] **Step 1: Create mkdocs.yml**

Create `docs/site/mkdocs.yml`:

```yaml
site_name: TenorTUI
site_description: A terminal UI for browsing stock options chains
site_url: https://jayravaliya.com/tenor-tui/
site_author: Jay Ravaliya

repo_name: jayrav13/tenor-tui
repo_url: https://github.com/jayrav13/tenor-tui
edit_uri: edit/main/docs/site/docs/

docs_dir: docs

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.instant
    - navigation.top
    - content.code.copy
    - content.code.annotate
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-night
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
  icon:
    repo: fontawesome/brands/github

markdown_extensions:
  - admonition
  - attr_list
  - md_in_html
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true

nav:
  - Home: index.md
  - Installation: installation.md
  - Quickstart: quickstart.md
  - Features:
      - Options chain: features/options-chain.md
      - Watchlists: features/watchlists.md
      - Providers: features/providers.md
      - Keybindings: features/keybindings.md
  - Configuration: configuration.md
  - Contributing: contributing.md
```

Note: `social` plugin is intentionally omitted — it requires Cairo system libs and adds CI complexity. We can add it later if we want auto-generated OG cards.

- [ ] **Step 2: Create the index page**

Create `docs/site/docs/index.md`:

```markdown
# TenorTUI

A terminal UI for browsing stock options chains. Live quotes, full options chains
with Greeks, named watchlists, and pluggable data providers — all in your terminal.

![TenorTUI showing AAPL options chain](assets/snapshots/hero.svg){ loading=lazy }

## Why a TUI?

- **Fast.** Keyboard-driven. No tab-switching, no clicking, no dashboards to load.
- **Offline-friendly.** Works in any terminal, including over SSH.
- **Composable.** Pipe-friendly architecture; pluggable data providers.
- **Free.** Yahoo Finance provider needs no API keys. Tradier optional.

## Try it in 30 seconds

```bash
pipx install tenor-tui
tenortui
```

Then type `AAPL` (or any ticker) and press Enter.

## See it in action

![Launching the app and loading AAPL](assets/demos/launch-and-search.gif){ loading=lazy }

## Where next?

- **[Installation](installation.md)** — pipx, pip, or from source
- **[Quickstart](quickstart.md)** — your first 60 seconds with the app
- **[Features](features/options-chain.md)** — the full guided tour
- **[Configuration](configuration.md)** — every option in `~/.config/tenor/config.yaml`
```

- [ ] **Step 3: Build the site (non-strict, since other pages don't exist yet)**

Run: `make docs`
Expected: `mkdocs build` succeeds with warnings about pages in `nav` that don't exist yet (`installation.md`, `quickstart.md`, etc.). Output written to `docs/site/site/`. Warnings are acceptable for now — Task 13 will get the build clean enough to pass `make docs-strict`.

- [ ] **Step 4: Add docs/site/site/ to .gitignore**

Add to `.gitignore`:

```
# MkDocs build output
docs/site/site/
```

- [ ] **Step 5: Serve the site locally and verify**

Run: `make docs-serve`
Expected: Site serves at http://127.0.0.1:8000. Open in browser, verify the index page renders with the hero SVG and the demo GIF visible.

Stop the server with Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add docs/site/mkdocs.yml docs/site/docs/index.md .gitignore
git commit -m "$(cat <<'EOF'
feat: add MkDocs Material site config and index page

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Write installation.md and quickstart.md

**Files:**
- Create: `docs/site/docs/installation.md`
- Create: `docs/site/docs/quickstart.md`

- [ ] **Step 1: Write installation.md**

```markdown
# Installation

TenorTUI requires **Python 3.11 or newer**.

## Recommended: pipx

[pipx](https://pipx.pypa.io/) installs Python apps in isolated environments
and puts the entry-point on your `PATH`.

```bash
pipx install tenor-tui
```

Then run:

```bash
tenortui
```

## Alternative: pip

```bash
pip install --user tenor-tui
```

You may need to add `~/.local/bin` to your `PATH` for the `tenortui` command
to be found.

## From source

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
poetry install
poetry run tenortui
```

## Configuration directory

On first launch, TenorTUI creates `~/.config/tenor/`:

- `config.yaml` — provider selection, theme, etc.
- `history.json` — recently viewed tickers
- `watchlists.json` — your watchlists

See [Configuration](configuration.md) for the full list of options.

## Choosing a provider

The default provider is **Yahoo Finance** — no API key required, no signup.

If you have a [Tradier](https://tradier.com/) account, you can use the Tradier
provider for richer Greeks data:

```bash
tenortui --provider tradier
```

See [Providers](features/providers.md) for the full comparison.
```

- [ ] **Step 2: Write quickstart.md**

```markdown
# Quickstart

This guide walks you through your first 60 seconds with TenorTUI.

## 1. Launch

```bash
tenortui
```

The app opens with a search bar at the top and (after your first ticker)
a "Recently Viewed" panel showing your watchlists.

![App on first launch](assets/snapshots/quote-bar.svg){ loading=lazy }

## 2. Search a ticker

Type a symbol and press <kbd>Enter</kbd>:

```text
AAPL
```

The quote bar populates with the live price, and the options-chain view loads
with calls on the left and puts on the right.

![AAPL chain loaded](assets/snapshots/hero.svg){ loading=lazy }

## 3. Switch expiries

Use <kbd>←</kbd> / <kbd>→</kbd> to switch between expiration date tabs.

![Expiry tabs](assets/snapshots/expiry-tabs.svg){ loading=lazy }

## 4. Add to a watchlist

Press <kbd>w</kbd> to open the watchlist picker. Pick a list (or create one
with <kbd>W</kbd>) and the current symbol is added.

![Watchlist picker](assets/snapshots/watchlist-modal.svg){ loading=lazy }

See the full keybinding reference in [Keybindings](features/keybindings.md).

## What's next

- Browse the [feature walkthrough](features/options-chain.md) to see everything
  the app can do.
- Read about the available [providers](features/providers.md) and how to
  configure them.
- Configure persistent options in `~/.config/tenor/config.yaml` — see
  [Configuration](configuration.md).
```

- [ ] **Step 3: Rebuild the site**

Run: `cd docs/site && poetry run mkdocs build`
Expected: Builds with fewer warnings (these two pages now exist).

- [ ] **Step 4: Verify in browser**

Run: `make docs-serve`
Click through Installation and Quickstart. Verify all images load.

- [ ] **Step 5: Commit**

```bash
git add docs/site/docs/installation.md docs/site/docs/quickstart.md
git commit -m "$(cat <<'EOF'
docs: add installation and quickstart pages

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Write features/options-chain.md and features/watchlists.md

**Files:**
- Create: `docs/site/docs/features/options-chain.md`
- Create: `docs/site/docs/features/watchlists.md`

- [ ] **Step 1: Write features/options-chain.md**

```markdown
# Options Chain

The options chain is the main view of TenorTUI: calls on the left, puts on the
right, with the at-the-money strike highlighted.

![AAPL options chain](../assets/snapshots/chain.svg){ loading=lazy }

## Layout

- **Calls table (left):** strike, bid, ask, last, volume, open interest, IV,
  and (if the provider supplies them) Δ Γ Θ ν ρ.
- **Puts table (right):** same columns, mirrored.
- **ATM divider row:** a horizontal divider sits at the strike closest to the
  current underlying price. The view auto-scrolls to keep it centered when you
  load a new chain.

## Expiry tabs

Each expiration date is a tab across the top of the chain. Switch with
<kbd>←</kbd> / <kbd>→</kbd> or click the tab.

![Expiry tabs](../assets/snapshots/expiry-tabs.svg){ loading=lazy }

## Greeks columns

Greeks columns appear automatically when the provider supplies them. The
default Yahoo provider does **not** include Greeks; the Tradier provider does.
See [Providers](providers.md) for the full capability matrix.

## Demo

![Loading and switching expiries](../assets/demos/expiry-and-greeks.gif){ loading=lazy }
```

- [ ] **Step 2: Write features/watchlists.md**

```markdown
# Watchlists

Watchlists group symbols you care about. They replaced the older "Recently
Viewed" panel — you can have multiple named watchlists, each containing
equity tickers and (optionally) specific options contracts.

![Watchlist picker](../assets/snapshots/watchlist-modal.svg){ loading=lazy }

## Keybindings

| Key | Action |
|---|---|
| <kbd>w</kbd> | Open the watchlist picker (add current symbol to a list) |
| <kbd>W</kbd> | Open the watchlist manager (create / rename / delete lists) |
| <kbd>d</kbd> | Delete the focused symbol from its list |
| <kbd>S</kbd> | Sort the focused list (cycles through symbol / price / change / volume) |

## Persistence

Watchlists are stored in `~/.config/tenor/watchlists.json`. The file is JSON,
human-readable, and safe to edit by hand if you want.

## Demo

![Add a symbol, switch lists](../assets/demos/watchlist-flow.gif){ loading=lazy }
```

- [ ] **Step 3: Rebuild and verify**

Run: `cd docs/site && poetry run mkdocs build` then `make docs-serve` and click through both new pages.

- [ ] **Step 4: Commit**

```bash
git add docs/site/docs/features/options-chain.md docs/site/docs/features/watchlists.md
git commit -m "$(cat <<'EOF'
docs: add options-chain and watchlists feature pages

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Write features/providers.md and features/keybindings.md

**Files:**
- Create: `docs/site/docs/features/providers.md`
- Create: `docs/site/docs/features/keybindings.md`

- [ ] **Step 1: Write features/providers.md**

```markdown
# Providers

TenorTUI is provider-agnostic: any class implementing the `DataProvider`
protocol can be plugged in. Two are included.

## Capability matrix

| Capability | Yahoo (default) | Tradier |
|---|---|---|
| Quotes | ✅ | ✅ |
| Expirations | ✅ | ✅ |
| Options chain | ✅ | ✅ |
| Implied volatility | ✅ | ✅ |
| Greeks (Δ Γ Θ ν ρ) | ❌ | ✅ |
| Authentication required | None | API key |

## Yahoo Finance (default)

No setup. The default provider uses the [yfinance](https://pypi.org/project/yfinance/)
library and works out of the box.

```bash
tenortui
# equivalent to
tenortui --provider yahoo
```

## Tradier

Requires a [Tradier](https://tradier.com/) account and API key. Add to
`~/.config/tenor/config.yaml`:

```yaml
provider: tradier
tradier:
  api_key: "YOUR_KEY_HERE"
  endpoint: "sandbox"  # or "production"
```

Then launch:

```bash
tenortui --provider tradier
```

## Fixture (development only)

A deterministic provider used for screenshots and demos. Returns frozen data
for AAPL and a placeholder for other symbols. Useful when you want a
reproducible UI state without making network calls.

```bash
tenortui --provider fixture
```

## Adding a new provider

Implement the `DataProvider` protocol from `src/tenortui/providers/base.py`:

```python
from typing import Protocol
from tenortui.models import Quote, OptionsChain

class DataProvider(Protocol):
    name: str
    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
```

Then register it in `src/tenortui/providers/__init__.py`'s `PROVIDERS` dict.
The CLI flag `--provider <name>` will pick it up.

See [Contributing](../contributing.md) for the dev workflow.
```

- [ ] **Step 2: Write features/keybindings.md**

```markdown
# Keybindings

A complete reference. Most keys are global; modal bindings only apply when
that modal is open.

## Global

| Key | Action |
|---|---|
| <kbd>/</kbd> | Focus the search bar |
| <kbd>Enter</kbd> | Submit (in search bar) |
| <kbd>Esc</kbd> | Close modal / unfocus |
| <kbd>q</kbd> | Quit |
| <kbd>r</kbd> | Refresh current chain |

## Options chain navigation

| Key | Action |
|---|---|
| <kbd>←</kbd> / <kbd>→</kbd> | Previous / next expiry |
| <kbd>↑</kbd> / <kbd>↓</kbd> | Scroll within the chain |
| <kbd>PageUp</kbd> / <kbd>PageDown</kbd> | Page through the chain |
| <kbd>Home</kbd> / <kbd>End</kbd> | Jump to first / last strike |

## Watchlists

| Key | Action |
|---|---|
| <kbd>w</kbd> | Add current symbol to a watchlist (opens picker) |
| <kbd>W</kbd> | Open the watchlist manager (create / rename / delete lists) |
| <kbd>d</kbd> | Delete focused symbol from its list |
| <kbd>S</kbd> | Sort focused list (cycles symbol / price / change / volume) |

!!! note
    Bindings are subject to change between minor versions. Run `tenortui --help`
    or check the in-app footer for the authoritative list at any moment.
```

- [ ] **Step 3: Rebuild and verify**

Run: `cd docs/site && poetry run mkdocs build` then `make docs-serve` and click through both new pages.

- [ ] **Step 4: Commit**

```bash
git add docs/site/docs/features/providers.md docs/site/docs/features/keybindings.md
git commit -m "$(cat <<'EOF'
docs: add providers and keybindings feature pages

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Write configuration.md and contributing.md, get build to pass --strict

**Files:**
- Create: `docs/site/docs/configuration.md`
- Create: `docs/site/docs/contributing.md`

- [ ] **Step 1: Inspect existing config options to make the table accurate**

Run: `poetry run tenortui --config-help`
Expected: Prints all available config options. Use the output to populate the table below.

If `--config-help` doesn't exist or output looks different, also inspect:

```bash
grep -A 100 "^CONFIG_OPTIONS" src/tenortui/config.py | head -120
```

- [ ] **Step 2: Write configuration.md**

Create `docs/site/docs/configuration.md`. Use the inspection from Step 1 to fill in the actual options. The structure is:

```markdown
# Configuration

TenorTUI loads YAML from `~/.config/tenor/config.yaml` (with `~/.tenorrc` as
a fallback). Every option is also discoverable via:

```bash
tenortui --config-help
```

## Example config.yaml

```yaml
provider: yahoo

tradier:
  api_key: ""
  endpoint: "sandbox"

theme: "dark"
```

## All options

<!-- Populate this table from `tenortui --config-help` output -->

| Key | Type | Default | Description |
|---|---|---|---|
| `provider` | string | `yahoo` | Data provider: `yahoo`, `tradier`, or `fixture` |
| `tradier.api_key` | string | (none) | Tradier API key (required if `provider: tradier`) |
| `tradier.endpoint` | string | `sandbox` | Tradier endpoint: `sandbox` or `production` |
<!-- Add a row for every other option in CONFIG_OPTIONS -->

## CLI flags

CLI flags override config file values for the current run.

| Flag | Description |
|---|---|
| `--provider <name>` | Override the configured provider |
| `--config-help` | Print all available config options and exit |
| `--version` | Print version and exit |

## Where data lives

| Path | Purpose |
|---|---|
| `~/.config/tenor/config.yaml` | Configuration |
| `~/.config/tenor/history.json` | Recently viewed tickers (max 10) |
| `~/.config/tenor/watchlists.json` | Named watchlists |
```

**Important:** the engineer running this plan must inspect the actual `CONFIG_OPTIONS` registry and fill in any options the placeholder rows omit. The placeholder must not be left in the committed file.

- [ ] **Step 3: Write contributing.md**

```markdown
# Contributing

Contributions welcome! This page is a quick orientation; the canonical
contribution flow lives in
[`CLAUDE.md`](https://github.com/jayrav13/tenor-tui/blob/main/CLAUDE.md)
in the repo.

## Local setup

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
poetry install --with docs
pre-commit install && pre-commit install --hook-type pre-push
poetry run tenortui
```

## Running tests

```bash
poetry run python -m pytest -v               # full suite
poetry run python -m pytest tests/test_xyz.py # one file
poetry run python -m pytest -k some_test     # by name
```

## Linting and formatting

```bash
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
```

The pre-commit hooks run `ruff check --fix` and `ruff format` on staged files
automatically.

## Working on the docs

The docs site lives under `docs/site/`. To preview changes locally:

```bash
make docs-serve
```

To regenerate screenshots and demo GIFs (after a UI change):

```bash
make snapshots
make demos
```

VHS (`brew install vhs`) is required for `make demos`.

## Issue and PR conventions

- Open an issue first; success criteria as a checkbox list helps reviewers.
- Branch off `main` with `fix/<issue-number>-<short-desc>`.
- Reference the issue (`Closes #N` or `Refs #N`) in commit messages.
- The project uses merge commits, not squash.

## License

MIT.
```

- [ ] **Step 4: Build with --strict**

Run: `make docs-strict`
Expected: `mkdocs build --strict` succeeds with **zero** warnings.

If it fails on broken links or missing images, fix them before continuing. The most common causes:
- Wrong relative path to an asset (use `../assets/...` from `features/*.md`, `assets/...` from top-level pages)
- Typo in a nav entry
- Page in `nav` doesn't exist

- [ ] **Step 5: Verify in browser**

Run: `make docs-serve`
Click through Configuration and Contributing. Verify the configuration table is fully populated (no `<!-- Populate -->` placeholder).

- [ ] **Step 6: Commit**

```bash
git add docs/site/docs/configuration.md docs/site/docs/contributing.md
git commit -m "$(cat <<'EOF'
docs: add configuration and contributing pages, build passes --strict

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Add docs-build job to ci.yml

**Files:**
- Modify: `.github/workflows/ci.yml`

**Why:** Catch broken links / missing assets in PRs before they hit `main`.

- [ ] **Step 1: Append docs-build job to ci.yml**

Add this job to `.github/workflows/ci.yml` (after the `test` job):

```yaml
  docs-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          virtualenvs-in-project: true

      - name: Load cached venv
        uses: actions/cache@v4
        with:
          path: .venv
          key: venv-docs-${{ hashFiles('**/poetry.lock') }}

      - name: Install dependencies
        run: poetry install --with docs

      - name: Build docs (strict)
        run: cd docs/site && poetry run mkdocs build --strict
```

- [ ] **Step 2: Commit and push to test the workflow**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
ci: add docs-build job to catch broken links in PRs

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Add docs deploy workflow

**Files:**
- Create: `.github/workflows/docs.yml`

**Why:** Automatically deploys the built site to the `gh-pages` branch on every merge to `main` that touches `docs/site/`.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy docs

on:
  push:
    branches: [main]
    paths:
      - "docs/site/**"
      - ".github/workflows/docs.yml"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          virtualenvs-in-project: true

      - name: Install dependencies
        run: poetry install --with docs

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

      - name: Deploy to gh-pages
        run: cd docs/site && poetry run mkdocs gh-deploy --force --remote-branch gh-pages
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "$(cat <<'EOF'
ci: add docs deploy workflow that pushes to gh-pages

Triggers on merge to main when docs/site/** changes. Uses mkdocs gh-deploy
to push the built site to the gh-pages branch, which GitHub Pages serves
at jayravaliya.com/tenor-tui/ once Pages is enabled on the repo.

Refs #45

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: Push, open PR, monitor CI, await user instruction

**Files:** none (this is process)

- [ ] **Step 1: Push the branch**

```bash
git push -u origin worktree-fix-45-stable-shipping
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "[Plan A] Docs site infrastructure (#45)" --body "$(cat <<'EOF'
## Summary

Plan A of the stable-shipping push (umbrella issue #45). Stands up the
MkDocs Material docs site with deterministic SVG snapshots and VHS demos.

- New `FixtureProvider` (deterministic data for snapshots/demos)
- `bin/snapshot` driving the Textual app via `Pilot` API → SVGs
- VHS `.tape` files → GIFs (run via `make demos`)
- MkDocs Material site under `docs/site/`
- `Makefile` with `snapshots`, `demos`, `docs`, `docs-serve` targets
- `docs-build` CI job (strict link checking)
- `docs.yml` deploy workflow (pushes to `gh-pages` on merge)

Plan B (PyPI release, README rewrite, CLAUDE.md docs sync, 1.0.0 bump)
will follow as a separate issue and PR.

## Test plan

- [ ] All existing tests still pass
- [ ] New `FixtureProvider` tests pass
- [ ] `bin/snapshot --list` exits 0
- [ ] `make snapshots` regenerates SVGs without errors
- [ ] `make demos` regenerates GIFs (requires `vhs` installed locally)
- [ ] `make docs` succeeds with `--strict` (no broken links)
- [ ] `make docs-serve` renders the site locally
- [ ] CI's new `docs-build` job passes
- [ ] After merge: `docs.yml` workflow runs and deploys to `gh-pages`
- [ ] After Pages enablement: site live at jayravaliya.com/tenor-tui/

## Manual follow-ups

- [ ] Enable GitHub Pages on the repo: Settings → Pages → Source: `gh-pages` branch
- [ ] Add `tenor-tui` to the sibling-Pages registry in `jayrav13.github.io`'s CLAUDE.md (path: `/tenor-tui/*`)

*Co-authored by Claude*
EOF
)"
```

- [ ] **Step 3: Monitor CI**

Run: `bin/ci-watch <pr-number> --poll 15`
Expected: All checks pass within a few minutes (lint, test on 3.11/3.12/3.13, docs-build).

If any check fails, investigate the failure and propose a fix. Do NOT merge.

- [ ] **Step 4: Provide local test command to user**

After CI passes, print the test command and copy to clipboard:

```bash
echo "cd $(pwd) && poetry install --with docs && poetry run tenortui --provider fixture"
echo -n "cd $(pwd) && poetry install --with docs && poetry run tenortui --provider fixture" | pbcopy
```

Tell the user to paste it into a separate terminal to test locally.

- [ ] **Step 5: Wait for explicit user instruction to merge**

Do NOT merge automatically. Wait for the user to say "merge it" or similar.

When merged: confirm the deploy workflow runs successfully (`gh run watch <run-id>`), then prompt the user to enable Pages and update the registry on the personal site.

---

## Self-Review (run before handing off to execution)

**Spec coverage check** — every Plan A item from the spec maps to a task above:

| Spec item | Task |
|---|---|
| `FixtureProvider` (Component 4 prerequisites) | 1, 2 |
| MkDocs site under `docs/site/` (Component 4) | 3, 9–13 |
| `bin/snapshot` script (Component 4) | 4, 5 |
| VHS tapes (Component 4) | 7, 8 |
| `Makefile` (Component 4) | 6 |
| `docs.yml` workflow (Component 4) | 15 |
| Docs build CI job | 14 |
| PR creation + CI monitoring | 16 |

**Placeholder scan:** the configuration.md page intentionally calls out "populate from `tenortui --config-help`" — this is a TODO inside a step's instructions, not a TODO in the final committed file. Step 5 of Task 13 explicitly verifies the placeholder is removed before commit. Acceptable.

**Type/method consistency:** `FixtureProvider.name == "fixture"` is consistent across registration (Task 2), CLI invocation (Task 7+ tapes), snapshot script (Task 4), and providers documentation (Task 12).

**Risks called out in spec but not yet mitigated:**
- VHS font availability on the user's machine — Task 7 Step 4 includes a fallback note.
- Snapshot determinism — handled by `FixtureProvider` design (Task 1).
- Pages domain conflict (sibling-repo registry on `jayrav13.github.io`) — flagged as a manual follow-up in Task 16's PR body.
