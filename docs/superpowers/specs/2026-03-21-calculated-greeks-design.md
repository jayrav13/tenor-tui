# Client-Side Greeks Calculation (Black-Scholes)

**Issue:** #9
**Date:** 2026-03-21

## Overview

Calculate Greeks client-side for the Yahoo Finance provider using a three-tier fallback modeled after `../tenor`'s QuantLib-based pipeline, reimplemented in pure Python with zero new dependencies.

## Greeks Calculation Engine

New module: `src/tenortui/greeks.py`

### Three-Tier Fallback

**Tier 1 — CRR Binomial American (200-step):**
- Pure Python Cox-Ross-Rubinstein binomial tree
- Handles early exercise (American-style options)
- Delta, gamma extracted from the tree; theta via 1-day time bump; vega/rho via finite difference (1% bumps)

**Tier 2 — Analytic Black-Scholes European:**
- Closed-form Black-Scholes-Merton with continuous dividend yield
- Pure Python normal CDF using Abramowitz & Stegun approximation (~7 decimal places)
- All Greeks computed analytically

**Tier 3 — Intrinsic Value:**
- `max(S-K, 0)` for calls, `max(K-S, 0)` for puts
- Delta = 1/-1 if ITM, 0 if OTM; all other Greeks = 0

**Routing:**
- IV <= 0 → intrinsic directly
- Time to expiry <= 0 (expiration day or past) → intrinsic directly
- Try American → on `Exception` → try European → on `Exception` → intrinsic

The `calculate_chain_greeks()` function never raises. It always succeeds — intrinsic is the ultimate safety net. Individual contract failures are silently caught and fall through to the next tier.

**Inputs per contract:** spot price, strike, IV, time to expiry (calendar days, as a year fraction), risk-free rate, dividend yield, option type.

### Time to Expiry

- Computed as calendar days from `date.today()` to expiration date, divided by 365.0
- Uses calendar days (standard for Black-Scholes), not trading days
- T <= 0 routes directly to intrinsic tier (avoids division by zero in d1/d2)

### Error Handling

- `math.domain` errors (e.g., `log` of negative), `ZeroDivisionError`, or any other `Exception` in a tier triggers fallback to the next tier
- `dividend_yield=None` is treated as 0.0
- The function always returns — never raises

## Data Flow & Integration

Calculation happens at the **app layer**, not inside the provider. This keeps the `DataProvider` protocol unchanged and the calculation logic decoupled.

**Flow in `app.py`:**
1. `_load_ticker` fetches quote — now includes `dividend_yield` (from `yfinance` `ticker.info`)
2. `_load_chain` fetches chain, then calls `calculate_chain_greeks()` if config enables it. This call happens inside the existing `@work` method, which already runs in a worker context, so the CPU-bound calculation does not block the UI.
3. `calculate_chain_greeks()` **mutates the chain in place** — it sets `delta`, `gamma`, `theta`, `vega`, `rho` on each `OptionContract` and sets `chain.greeks_calculated = True`
4. Chain now has Greeks populated → `ChainTable` renders them with `*` suffix on column headers

**Input sourcing:**
- **Spot price:** `self._current_price` already available in `app.py`
- **Dividend yield:** Added to `Quote` dataclass as `dividend_yield: float | None`, sourced from `yfinance` `info.get("dividendYield")`. Defaults to `0.0` if `None`.
- **Risk-free rate:** From config (`yahoo.greeks.risk_free_rate`, default 0.05)
- **Time to expiry:** Computed from expiration date string vs `date.today()`, calendar days / 365.0

### Model Changes

**`Quote` dataclass** — add `dividend_yield: float | None = None`:
- `YahooProvider.get_quote()`: populate from `info.get("dividendYield")`
- `TradierProvider.get_quote()`: set to `None` (not used by Tradier since it provides Greeks natively)
- `batch_quotes()` in `yahoo.py`: set to `None` (not needed for recently-viewed display)
- `FakeProvider` in `conftest.py`: set to `None` (or a test value where Greeks tests need it)

**`OptionsChain` dataclass** — add `greeks_calculated: bool = False`:
- Set to `True` by `calculate_chain_greeks()` after populating Greeks
- No changes needed in providers (defaults to `False`)

### Unchanged Files

- `providers/__init__.py` — no changes
- `providers/base.py` — `DataProvider` protocol unchanged

## Configuration

Under `yahoo:` in `~/.config/tenor/config.yaml`:

```yaml
yahoo:
  greeks:
    enabled: false          # off by default (these are approximations)
    risk_free_rate: 0.05    # static default, overridable
```

**Implementation:**
- New `GreeksConfig` dataclass in `config.py` with `enabled: bool = False` and `risk_free_rate: float = 0.05`
- Add `greeks: GreeksConfig` field to `AppConfig` (default `GreeksConfig()`)
- Parse from `provider_config` dict: when `provider_name == "yahoo"`, look for `provider_config.get("greeks", {})` and build `GreeksConfig` from it
- `app.py` checks `config.greeks.enabled` to decide whether to calculate

## Visual Indicator

When Greeks are calculated client-side, column headers get a `*` suffix:

```
Strike  Bid   Ask   Spread  Mid   Last  Vol   OI    IV    Delta*  Gamma*  Theta*  Vega*  Rho*
```

- `ChainTable.display_chain()` reads `chain.greeks_calculated` and dynamically builds the column list using `("Delta*", 8)` etc. instead of the module-level `GREEK_COLUMNS` constant
- Provider-sourced Greeks (Tradier) have `greeks_calculated=False`, so no suffix

## Testing

- **Unit tests for `greeks.py`:** All three tiers validated against known Black-Scholes values. Reference test case: call with S=100, K=100, T=1yr, r=0.05, sigma=0.20, q=0 — expected Delta≈0.6368, Gamma≈0.0188, Theta≈-0.0176/day, Vega≈0.3752, Rho≈0.5323 (within 0.01 absolute tolerance).
- **Fallback routing tests:** Zero IV → intrinsic. Zero time to expiry → intrinsic. Forced American failure → European. Forced European failure → intrinsic.
- **Integration tests:** `calculate_chain_greeks()` on a mock `OptionsChain` with known inputs, verify all contracts populated.
- **Config tests:** Verify `yahoo.greeks` parsing, defaults, missing section, and that the flag gates calculation.
- **Model tests:** `Quote` with `dividend_yield`, `OptionsChain` with `greeks_calculated` flag.
- **Fixture updates:** `FakeProvider` and all test `Quote` constructions updated with `dividend_yield` field.

## Performance

A 200-step CRR binomial tree in pure Python takes ~1-5ms per contract. For a typical chain (~100 contracts), total calculation time is ~100-500ms. This is well within acceptable limits given that the API call itself takes 1-3 seconds. The calculation runs inside the existing `@work` method (worker thread), so it does not block the UI.

## Follow-up Issues

- **Live risk-free rate:** Fetch current Treasury yields from an API instead of the static config default (separate issue/PR).
- **Config help mechanism:** Surface all YAML config options to users (separate issue).

## Dependencies

None. Pure Python using only `math` standard library module.
