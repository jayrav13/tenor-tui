# Client-Side Greeks Calculation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calculate Greeks client-side for the Yahoo Finance provider using a three-tier fallback (American binomial → European Black-Scholes → intrinsic) in pure Python.

**Architecture:** New `greeks.py` module implements all three pricing tiers with zero external dependencies. Calculation is triggered at the app layer after `get_chain()` returns, gated by a `yahoo.greeks.enabled` config flag. Calculated Greeks are visually distinguished with `*` column header suffixes.

**Tech Stack:** Python 3.11+, `math` stdlib only for calculations. Textual for UI. pytest for testing.

**Spec:** `docs/superpowers/specs/2026-03-21-calculated-greeks-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/tenortui/greeks.py` | Three-tier Greeks calculation engine |
| Create | `tests/test_greeks.py` | Unit tests for all three tiers + fallback routing |
| Modify | `src/tenortui/models.py` | Add `dividend_yield` to `Quote`, `greeks_calculated` to `OptionsChain` |
| Modify | `src/tenortui/config.py` | Add `GreeksConfig` dataclass, parse `yahoo.greeks` section |
| Modify | `src/tenortui/providers/yahoo.py` | Populate `dividend_yield` in `get_quote()` |
| Modify | `src/tenortui/providers/tradier.py` | Set `dividend_yield=None` in `get_quote()` |
| Modify | `src/tenortui/widgets/chain_table.py` | Dynamic `*` suffix on Greek column headers |
| Modify | `src/tenortui/app.py` | Wire Greeks calculation into `_load_chain` flow |
| Modify | `tests/conftest.py` | Update fixtures with new fields |
| Modify | `tests/test_models.py` | Tests for new model fields |
| Modify | `tests/test_config.py` | Tests for `GreeksConfig` parsing |
| Modify | `tests/test_yahoo_provider.py` | Verify `dividend_yield` populated |

---

### Task 1: Update `Quote` and `OptionsChain` Models

**Files:**
- Modify: `src/tenortui/models.py:5-13` (Quote dataclass)
- Modify: `src/tenortui/models.py:48-53` (OptionsChain dataclass)
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for new model fields**

Add to `tests/test_models.py`:

```python
class TestQuote:
    # ... existing tests ...

    def test_dividend_yield_default_none(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
        )
        assert q.dividend_yield is None

    def test_dividend_yield_set(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
            dividend_yield=0.0055,
        )
        assert q.dividend_yield == 0.0055


class TestOptionsChain:
    # ... existing tests ...

    def test_greeks_calculated_default_false(self):
        chain = OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=[], puts=[])
        assert chain.greeks_calculated is False

    def test_greeks_calculated_set_true(self):
        chain = OptionsChain(
            symbol="AAPL", expiration="2026-03-21", calls=[], puts=[],
            greeks_calculated=True,
        )
        assert chain.greeks_calculated is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_models.py -v`
Expected: FAIL — `dividend_yield` and `greeks_calculated` not defined

- [ ] **Step 3: Add fields to models**

In `src/tenortui/models.py`, add to `Quote`:

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
    dividend_yield: float | None = None
```

Add to `OptionsChain`:

```python
@dataclass
class OptionsChain:
    symbol: str
    expiration: str
    calls: list[OptionContract]
    puts: list[OptionContract]
    greeks_calculated: bool = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `poetry run python -m pytest -v`
Expected: All PASS (default values ensure backward compatibility)

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/models.py tests/test_models.py
git commit -m "feat: add dividend_yield to Quote and greeks_calculated to OptionsChain

Closes #9 (partial)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Add `GreeksConfig` to Configuration

**Files:**
- Modify: `src/tenortui/config.py:30-41` (AppConfig dataclass area)
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for GreeksConfig parsing**

Add to `tests/test_config.py`:

```python
from tenortui.config import GreeksConfig, SpreadThresholds, load_config, resolve_config_path


class TestGreeksConfig:
    def test_defaults_when_no_config(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.greeks.enabled is False
        assert config.greeks.risk_free_rate == 0.05

    def test_greeks_enabled(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo:\n  greeks:\n    enabled: true\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is True
        assert config.greeks.risk_free_rate == 0.05

    def test_custom_risk_free_rate(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nyahoo:\n  greeks:\n    enabled: true\n    risk_free_rate: 0.04\n"
        )
        config = load_config(config_path=rc)
        assert config.greeks.risk_free_rate == 0.04

    def test_greeks_not_parsed_for_tradier(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: tradier\ntradier:\n  api_key: abc\n  greeks:\n    enabled: true\n"
        )
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False

    def test_greeks_with_provider_override(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\nyahoo:\n  greeks:\n    enabled: true\n")
        config = load_config(config_path=rc, provider_override="yahoo")
        assert config.greeks.enabled is True

    def test_greeks_missing_section_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False
        assert config.greeks.risk_free_rate == 0.05

    def test_greeks_invalid_section_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo:\n  greeks: not_a_dict\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_config.py::TestGreeksConfig -v`
Expected: FAIL — `GreeksConfig` not defined

- [ ] **Step 3: Implement GreeksConfig**

In `src/tenortui/config.py`, add:

```python
@dataclass
class GreeksConfig:
    enabled: bool = False
    risk_free_rate: float = 0.05
```

Update `AppConfig`:

```python
@dataclass
class AppConfig:
    provider_name: str
    provider_config: dict = field(default_factory=dict)
    spread_thresholds: SpreadThresholds = field(default_factory=SpreadThresholds)
    greeks: GreeksConfig = field(default_factory=GreeksConfig)
```

Add a parser function:

```python
def _parse_greeks_config(provider_name: str, provider_config: dict) -> GreeksConfig:
    """Parse greeks config from provider section. Only applies to Yahoo."""
    if provider_name != "yahoo":
        return GreeksConfig()
    section = provider_config.get("greeks")
    if not isinstance(section, dict):
        return GreeksConfig()
    return GreeksConfig(
        enabled=bool(section.get("enabled", False)),
        risk_free_rate=float(section.get("risk_free_rate", 0.05)),
    )
```

Wire it into `load_config()` — in both the override path and the normal path, add `greeks=_parse_greeks_config(provider_name, provider_config)` to the `AppConfig` constructor calls.

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/config.py tests/test_config.py
git commit -m "feat: add GreeksConfig for yahoo.greeks settings

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Implement Greeks Calculation Engine — Intrinsic Tier

**Files:**
- Create: `src/tenortui/greeks.py`
- Create: `tests/test_greeks.py`

- [ ] **Step 1: Write failing tests for intrinsic tier**

Create `tests/test_greeks.py`:

```python
from tenortui.greeks import calculate_intrinsic


class TestIntrinsicTier:
    def test_call_itm(self):
        result = calculate_intrinsic(
            spot=110.0, strike=100.0, option_type="call"
        )
        assert result["delta"] == 1.0
        assert result["gamma"] == 0.0
        assert result["theta"] == 0.0
        assert result["vega"] == 0.0
        assert result["rho"] == 0.0
        assert result["price"] == 10.0
        assert result["model"] == "intrinsic"

    def test_call_otm(self):
        result = calculate_intrinsic(
            spot=90.0, strike=100.0, option_type="call"
        )
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_put_itm(self):
        result = calculate_intrinsic(
            spot=90.0, strike=100.0, option_type="put"
        )
        assert result["delta"] == -1.0
        assert result["price"] == 10.0

    def test_put_otm(self):
        result = calculate_intrinsic(
            spot=110.0, strike=100.0, option_type="put"
        )
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_call_atm(self):
        result = calculate_intrinsic(
            spot=100.0, strike=100.0, option_type="call"
        )
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_put_atm(self):
        result = calculate_intrinsic(
            spot=100.0, strike=100.0, option_type="put"
        )
        assert result["delta"] == 0.0
        assert result["price"] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_greeks.py::TestIntrinsicTier -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement intrinsic tier**

Create `src/tenortui/greeks.py`:

```python
"""
Client-side Greeks calculation engine.

Three-tier fallback chain:
  1. CRR Binomial American (200-step)
  2. Black-Scholes European (analytic)
  3. Intrinsic value (arithmetic)

Pure Python — no external dependencies.
"""

import math
from datetime import date


def calculate_intrinsic(spot: float, strike: float, option_type: str) -> dict:
    """Tier 3: Pure arithmetic fallback for zero/negative IV."""
    if option_type == "put":
        price = max(strike - spot, 0.0)
        delta = -1.0 if spot < strike else 0.0
    else:
        price = max(spot - strike, 0.0)
        delta = 1.0 if spot > strike else 0.0

    return {
        "delta": delta,
        "gamma": 0.0,
        "theta": 0.0,
        "vega": 0.0,
        "rho": 0.0,
        "price": round(price, 6),
        "model": "intrinsic",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_greeks.py::TestIntrinsicTier -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/greeks.py tests/test_greeks.py
git commit -m "feat: add intrinsic value tier for Greeks calculation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Implement Greeks Calculation Engine — European (Black-Scholes) Tier

**Files:**
- Modify: `src/tenortui/greeks.py`
- Modify: `tests/test_greeks.py`

- [ ] **Step 1: Write failing tests for European tier**

Add to `tests/test_greeks.py`:

```python
from tenortui.greeks import calculate_european


class TestEuropeanTier:
    """Validated against textbook Black-Scholes values.

    Reference: S=100, K=100, T=1yr, r=0.05, sigma=0.20, q=0
    Expected (Hull, Options Futures & Other Derivatives):
        Call: Delta≈0.6368, Gamma≈0.0188, Theta≈-0.0176/day,
              Vega≈0.3752, Rho≈0.5323
        Put:  Delta≈-0.3632, Rho≈-0.4189
    """

    def test_call_atm(self):
        result = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["model"] == "european"
        assert abs(result["delta"] - 0.6368) < 0.01
        assert abs(result["gamma"] - 0.0188) < 0.01
        assert abs(result["theta"] - (-0.0176)) < 0.01
        assert abs(result["vega"] - 0.3752) < 0.01
        assert abs(result["rho"] - 0.5323) < 0.01

    def test_put_atm(self):
        result = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="put",
        )
        assert result["model"] == "european"
        assert abs(result["delta"] - (-0.3632)) < 0.01
        assert abs(result["rho"] - (-0.4189)) < 0.01

    def test_deep_itm_call(self):
        result = calculate_european(
            spot=150.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["delta"] > 0.95

    def test_deep_otm_call(self):
        result = calculate_european(
            spot=50.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["delta"] < 0.05

    def test_with_dividend_yield(self):
        result = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.02, option_type="call",
        )
        # Dividend yield reduces call delta
        no_div = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["delta"] < no_div["delta"]

    def test_short_expiry(self):
        result = calculate_european(
            spot=100.0, strike=100.0, T=1/365, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["model"] == "european"
        # Near-expiry ATM delta should be close to 0.5
        assert abs(result["delta"] - 0.5) < 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_greeks.py::TestEuropeanTier -v`
Expected: FAIL — `calculate_european` not defined

- [ ] **Step 3: Implement normal CDF and European tier**

Add to `src/tenortui/greeks.py`:

```python
def _norm_cdf(x: float) -> float:
    """Cumulative normal distribution. Abramowitz & Stegun approximation."""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)
    return 0.5 * (1.0 + sign * y)


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def calculate_european(
    spot: float, strike: float, T: float, r: float,
    sigma: float, q: float, option_type: str,
) -> dict:
    """Tier 2: Analytic Black-Scholes-Merton European engine."""
    sqrt_T = math.sqrt(T)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    exp_qT = math.exp(-q * T)
    exp_rT = math.exp(-r * T)

    if option_type == "call":
        delta = exp_qT * _norm_cdf(d1)
        price = spot * exp_qT * _norm_cdf(d1) - strike * exp_rT * _norm_cdf(d2)
        rho = strike * T * exp_rT * _norm_cdf(d2) / 100.0
    else:
        delta = -exp_qT * _norm_cdf(-d1)
        price = strike * exp_rT * _norm_cdf(-d2) - spot * exp_qT * _norm_cdf(-d1)
        rho = -strike * T * exp_rT * _norm_cdf(-d2) / 100.0

    gamma = exp_qT * _norm_pdf(d1) / (spot * sigma * sqrt_T)
    theta = (
        -(spot * sigma * exp_qT * _norm_pdf(d1)) / (2.0 * sqrt_T)
        - r * strike * exp_rT * _norm_cdf(d2 if option_type == "call" else -d2)
            * (1.0 if option_type == "call" else -1.0)
        + q * spot * exp_qT * _norm_cdf(d1 if option_type == "call" else -d1)
            * (1.0 if option_type == "call" else -1.0)
    ) / 365.0
    vega = spot * exp_qT * _norm_pdf(d1) * sqrt_T / 100.0

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "theta": round(theta, 6),
        "vega": round(vega, 6),
        "rho": round(rho, 6),
        "price": round(price, 6),
        "model": "european",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_greeks.py::TestEuropeanTier -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/greeks.py tests/test_greeks.py
git commit -m "feat: add Black-Scholes European tier for Greeks calculation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Implement Greeks Calculation Engine — American (CRR Binomial) Tier

**Files:**
- Modify: `src/tenortui/greeks.py`
- Modify: `tests/test_greeks.py`

- [ ] **Step 1: Write failing tests for American tier**

Add to `tests/test_greeks.py`:

```python
from tenortui.greeks import calculate_american


class TestAmericanTier:
    """CRR binomial should be close to European for no-dividend calls,
    and should price higher than European for puts (early exercise premium)."""

    def test_call_no_dividend_matches_european(self):
        """Without dividends, American call == European call."""
        american = calculate_american(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        european = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert american["model"] == "american"
        assert abs(american["delta"] - european["delta"]) < 0.02
        assert abs(american["price"] - european["price"]) < 0.5

    def test_put_early_exercise_premium(self):
        """American put should be worth >= European put."""
        american = calculate_american(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="put",
        )
        european = calculate_european(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="put",
        )
        assert american["price"] >= european["price"] - 0.01

    def test_deep_itm_put(self):
        american = calculate_american(
            spot=50.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="put",
        )
        assert american["delta"] < -0.9
        assert american["price"] > 45.0

    def test_greeks_have_correct_signs(self):
        call = calculate_american(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert call["delta"] > 0
        assert call["gamma"] > 0
        assert call["theta"] < 0
        assert call["vega"] > 0
        assert call["rho"] > 0

        put = calculate_american(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="put",
        )
        assert put["delta"] < 0
        assert put["gamma"] > 0
        assert put["theta"] < 0
        assert put["vega"] > 0
        assert put["rho"] < 0

    def test_with_dividend_yield(self):
        result = calculate_american(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.02, option_type="call",
        )
        assert result["model"] == "american"
        # With dividend, American call may have early exercise value
        assert result["delta"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_greeks.py::TestAmericanTier -v`
Expected: FAIL — `calculate_american` not defined

- [ ] **Step 3: Implement CRR binomial American tier**

Add to `src/tenortui/greeks.py`:

```python
def calculate_american(
    spot: float, strike: float, T: float, r: float,
    sigma: float, q: float, option_type: str,
    steps: int = 200,
) -> dict:
    """Tier 1: CRR Binomial American engine."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    div_disc = math.exp(-q * dt)
    p = (math.exp((r - q) * dt) - d) / (u - d)

    is_call = option_type == "call"

    # Build terminal payoffs
    prices = [spot * (u ** (steps - 2 * j)) for j in range(steps + 1)]
    if is_call:
        values = [max(px - strike, 0.0) for px in prices]
    else:
        values = [max(strike - px, 0.0) for px in prices]

    # Backward induction with early exercise
    for i in range(steps - 1, -1, -1):
        new_prices = [spot * (u ** (i - 2 * j)) for j in range(i + 1)]
        new_values = []
        for j in range(i + 1):
            hold = disc * (p * values[j] + (1.0 - p) * values[j + 1])
            if is_call:
                exercise = max(new_prices[j] - strike, 0.0)
            else:
                exercise = max(strike - new_prices[j], 0.0)
            new_values.append(max(hold, exercise))
        prices = new_prices
        values = new_values

        # Capture values at step 1 and step 2 for delta/gamma
        if i == 2:
            v_uu = values[0]
            v_ud = values[1]
            v_dd = values[2]
            p_uu = prices[0]
            p_ud = prices[1]
            p_dd = prices[2]
        if i == 1:
            v_u = values[0]
            v_d = values[1]
            p_u = prices[0]
            p_d = prices[1]

    price = values[0]

    # Delta from first step
    delta = (v_u - v_d) / (p_u - p_d)

    # Gamma from second step
    delta_u = (v_uu - v_ud) / (p_uu - p_ud)
    delta_d = (v_ud - v_dd) / (p_ud - p_dd)
    gamma = (delta_u - delta_d) / ((p_uu - p_dd) / 2.0)

    # Theta via finite difference: re-run with T - 1/365
    dt_bump = 1.0 / 365.0
    if T > dt_bump:
        price_t1 = _american_price(spot, strike, T - dt_bump, r, sigma, q, is_call, steps)
        theta = price_t1 - price  # already per-day since we bumped by 1 day
    else:
        theta = 0.0

    # Vega via finite difference: bump sigma by 0.01
    dsigma = 0.01
    price_up_vol = _american_price(spot, strike, T, r, sigma + dsigma, q, is_call, steps)
    vega = (price_up_vol - price) / (dsigma * 100.0)

    # Rho via finite difference: bump r by 0.01
    dr = 0.01
    price_up_rate = _american_price(spot, strike, T, r + dr, sigma, q, is_call, steps)
    rho = (price_up_rate - price) / (dr * 100.0)

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "theta": round(theta, 6),
        "vega": round(vega, 6),
        "rho": round(rho, 6),
        "price": round(price, 6),
        "model": "american",
    }


def _american_price(
    spot: float, strike: float, T: float, r: float,
    sigma: float, q: float, is_call: bool, steps: int,
) -> float:
    """Compute American option price only (no Greeks). Used for finite differences."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    p = (math.exp((r - q) * dt) - d) / (u - d)

    prices = [spot * (u ** (steps - 2 * j)) for j in range(steps + 1)]
    if is_call:
        values = [max(px - strike, 0.0) for px in prices]
    else:
        values = [max(strike - px, 0.0) for px in prices]

    for i in range(steps - 1, -1, -1):
        new_prices = [spot * (u ** (i - 2 * j)) for j in range(i + 1)]
        new_values = []
        for j in range(i + 1):
            hold = disc * (p * values[j] + (1.0 - p) * values[j + 1])
            if is_call:
                exercise = max(new_prices[j] - strike, 0.0)
            else:
                exercise = max(strike - new_prices[j], 0.0)
            new_values.append(max(hold, exercise))
        prices = new_prices
        values = new_values

    return values[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_greeks.py::TestAmericanTier -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/greeks.py tests/test_greeks.py
git commit -m "feat: add CRR binomial American tier for Greeks calculation

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Implement Fallback Router and `calculate_chain_greeks()`

**Files:**
- Modify: `src/tenortui/greeks.py`
- Modify: `tests/test_greeks.py`

- [ ] **Step 1: Write failing tests for routing and chain calculation**

Add to `tests/test_greeks.py`:

```python
from tenortui.greeks import calculate_greeks, calculate_chain_greeks
from tenortui.models import OptionContract, OptionsChain


class TestFallbackRouting:
    def test_zero_iv_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0, strike=90.0, T=1.0, r=0.05,
            sigma=0.0, q=0.0, option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_negative_iv_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0, strike=90.0, T=1.0, r=0.05,
            sigma=-0.1, q=0.0, option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_zero_time_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0, strike=90.0, T=0.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_negative_time_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0, strike=90.0, T=-1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_normal_inputs_use_american(self):
        result = calculate_greeks(
            spot=100.0, strike=100.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert result["model"] == "american"

    def test_never_raises(self):
        """Even with absurd inputs, should return a result."""
        result = calculate_greeks(
            spot=0.0, strike=0.0, T=1.0, r=0.05,
            sigma=0.20, q=0.0, option_type="call",
        )
        assert "delta" in result


class TestCalculateChainGreeks:
    def _make_contract(self, strike, option_type="call", iv=0.30):
        return OptionContract(
            contract_symbol=f"TEST{strike}{option_type[0].upper()}",
            option_type=option_type,
            strike=strike,
            bid=5.0, ask=5.50, last_price=5.25,
            volume=100, open_interest=500,
            implied_volatility=iv,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        )

    def test_populates_greeks_on_all_contracts(self):
        chain = OptionsChain(
            symbol="TEST", expiration="2027-03-21",
            calls=[self._make_contract(100.0), self._make_contract(110.0)],
            puts=[self._make_contract(100.0, "put"), self._make_contract(110.0, "put")],
        )
        calculate_chain_greeks(
            chain=chain, spot=105.0, expiration="2027-03-21",
            risk_free_rate=0.05, dividend_yield=0.0,
        )
        assert chain.greeks_calculated is True
        for contract in chain.calls + chain.puts:
            assert contract.delta is not None
            assert contract.gamma is not None
            assert contract.theta is not None
            assert contract.vega is not None
            assert contract.rho is not None

    def test_call_deltas_positive_put_deltas_negative(self):
        chain = OptionsChain(
            symbol="TEST", expiration="2027-03-21",
            calls=[self._make_contract(100.0)],
            puts=[self._make_contract(100.0, "put")],
        )
        calculate_chain_greeks(
            chain=chain, spot=105.0, expiration="2027-03-21",
            risk_free_rate=0.05, dividend_yield=0.0,
        )
        assert chain.calls[0].delta > 0
        assert chain.puts[0].delta < 0

    def test_none_dividend_yield_treated_as_zero(self):
        chain = OptionsChain(
            symbol="TEST", expiration="2027-03-21",
            calls=[self._make_contract(100.0)],
            puts=[],
        )
        calculate_chain_greeks(
            chain=chain, spot=105.0, expiration="2027-03-21",
            risk_free_rate=0.05, dividend_yield=None,
        )
        assert chain.calls[0].delta is not None

    def test_expired_chain_uses_intrinsic(self):
        chain = OptionsChain(
            symbol="TEST", expiration="2020-01-01",
            calls=[self._make_contract(100.0)],
            puts=[],
        )
        calculate_chain_greeks(
            chain=chain, spot=105.0, expiration="2020-01-01",
            risk_free_rate=0.05, dividend_yield=0.0,
        )
        assert chain.greeks_calculated is True
        assert chain.calls[0].delta == 1.0  # ITM call intrinsic
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_greeks.py::TestFallbackRouting tests/test_greeks.py::TestCalculateChainGreeks -v`
Expected: FAIL — `calculate_greeks` and `calculate_chain_greeks` not defined

- [ ] **Step 3: Implement routing and chain function**

Add to `src/tenortui/greeks.py`:

```python
def calculate_greeks(
    spot: float, strike: float, T: float, r: float,
    sigma: float, q: float, option_type: str,
) -> dict:
    """Calculate Greeks using three-tier fallback. Never raises."""
    try:
        if T <= 0 or sigma <= 0:
            return calculate_intrinsic(spot, strike, option_type)

        # Tier 1: CRR Binomial American
        try:
            return calculate_american(spot, strike, T, r, sigma, q, option_type)
        except Exception:
            pass

        # Tier 2: Black-Scholes European
        try:
            return calculate_european(spot, strike, T, r, sigma, q, option_type)
        except Exception:
            pass

        # Tier 3: Intrinsic value
        return calculate_intrinsic(spot, strike, option_type)

    except Exception:
        return calculate_intrinsic(spot, strike, option_type)


def calculate_chain_greeks(
    chain, spot: float, expiration: str,
    risk_free_rate: float, dividend_yield: float | None,
) -> None:
    """Populate Greeks on all contracts in the chain. Mutates in place."""
    q = dividend_yield if dividend_yield is not None else 0.0
    exp_date = date.fromisoformat(expiration)
    T = (exp_date - date.today()).days / 365.0

    for contract in chain.calls + chain.puts:
        sigma = contract.implied_volatility if contract.implied_volatility is not None else 0.0
        result = calculate_greeks(
            spot=spot,
            strike=contract.strike,
            T=T,
            r=risk_free_rate,
            sigma=sigma,
            q=q,
            option_type=contract.option_type,
        )
        contract.delta = result["delta"]
        contract.gamma = result["gamma"]
        contract.theta = result["theta"]
        contract.vega = result["vega"]
        contract.rho = result["rho"]

    chain.greeks_calculated = True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_greeks.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/greeks.py tests/test_greeks.py
git commit -m "feat: add fallback router and calculate_chain_greeks function

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Update Providers — `dividend_yield` in Yahoo and Tradier

**Files:**
- Modify: `src/tenortui/providers/yahoo.py:34-42` (get_quote return)
- Modify: `src/tenortui/providers/yahoo.py:107-116` (batch_quotes)
- Modify: `src/tenortui/providers/tradier.py:54-62` (get_quote return)
- Modify: `tests/test_yahoo_provider.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing test for Yahoo dividend_yield**

Add to `tests/test_yahoo_provider.py` in `TestYahooProviderGetQuote`:

```python
    def test_dividend_yield_populated(self):
        info = _load_fixture("yahoo_quote.json")
        info["dividendYield"] = 0.0055
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("AAPL")
        assert quote.dividend_yield == 0.0055

    def test_dividend_yield_none_when_missing(self):
        info = _load_fixture("yahoo_quote.json")
        info.pop("dividendYield", None)
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("AAPL")
        assert quote.dividend_yield is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_yahoo_provider.py::TestYahooProviderGetQuote::test_dividend_yield_populated -v`
Expected: FAIL

- [ ] **Step 3: Update Yahoo provider**

In `src/tenortui/providers/yahoo.py`, update `get_quote()` return:

```python
        return Quote(
            symbol=symbol.upper(),
            name=info.get("shortName", symbol),
            price=info["regularMarketPrice"],
            change=info.get("regularMarketChange", 0.0),
            change_percent=info.get("regularMarketChangePercent", 0.0),
            volume=info.get("regularMarketVolume", 0),
            market_cap=info.get("marketCap"),
            dividend_yield=info.get("dividendYield"),
        )
```

Update Tradier `get_quote()` — no changes needed since `dividend_yield` defaults to `None`.

Update `conftest.py` `sample_quote` — no changes needed since `dividend_yield` defaults to `None`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_yahoo_provider.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/providers/yahoo.py tests/test_yahoo_provider.py
git commit -m "feat: populate dividend_yield in Yahoo provider get_quote

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Update ChainTable for `*` Column Headers

**Files:**
- Modify: `src/tenortui/widgets/chain_table.py:70-77` (display_chain)
- Modify: `tests/test_widgets_coverage.py` (or add to existing widget tests)

- [ ] **Step 1: Write failing test for starred headers**

Add to `tests/test_widgets_coverage.py`. Follow the existing pattern: use `WidgetTestApp` to mount `ChainTable` in isolation and the `_make_contract` helper already in that file.

```python
@pytest.mark.asyncio
async def test_chain_table_calculated_greeks_starred_headers():
    """When greeks_calculated is True, Greek column headers should have * suffix."""
    chain = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[_make_contract(200.0, with_greeks=True)],
        puts=[_make_contract(200.0, "put", with_greeks=True)],
        greeks_calculated=True,
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=205.0)
        from textual.widgets import DataTable

        tables = widget.query(DataTable)
        for table in tables:
            col_labels = [str(col.label) for col in table.columns.values()]
            greek_labels = [c for c in col_labels if "Delta" in c]
            assert len(greek_labels) > 0
            assert all("*" in c for c in greek_labels)


@pytest.mark.asyncio
async def test_chain_table_provider_greeks_no_star():
    """When greeks_calculated is False, Greek column headers have no * suffix."""
    chain = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[_make_contract(200.0, with_greeks=True)],
        puts=[_make_contract(200.0, "put", with_greeks=True)],
        greeks_calculated=False,
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=205.0)
        from textual.widgets import DataTable

        tables = widget.query(DataTable)
        for table in tables:
            col_labels = [str(col.label) for col in table.columns.values()]
            greek_labels = [c for c in col_labels if "Delta" in c]
            assert len(greek_labels) > 0
            assert not any("*" in c for c in greek_labels)
```

- [ ] **Step 2: Run tests to verify they fail**

Run the relevant test file.
Expected: FAIL

- [ ] **Step 3: Update ChainTable**

In `src/tenortui/widgets/chain_table.py`, modify `display_chain()`:

```python
    async def display_chain(
        self,
        chain: OptionsChain,
        current_price: float | None = None,
        spread_thresholds: SpreadThresholds | None = None,
    ) -> None:
        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        if show_greeks and chain.greeks_calculated:
            greek_cols = [
                ("Delta*", 8), ("Gamma*", 8), ("Theta*", 8), ("Vega*", 8), ("Rho*", 8),
            ]
        else:
            greek_cols = GREEK_COLUMNS
        columns = BASE_COLUMNS + (greek_cols if show_greeks else [])
        # ... rest of method unchanged
```

Also update `_populate_table` to handle starred column names. Replace the existing check at line 145-147:

```python
            if any(
                col[0] in ("Delta", "Gamma", "Theta", "Vega", "Rho") for col in columns
            ):
```

with:

```python
            if any(
                col[0].rstrip("*") in ("Delta", "Gamma", "Theta", "Vega", "Rho")
                for col in columns
            ):
```

Also update the `add_column` call in `_populate_table` to strip `*` from keys so column keys remain consistent:

```python
        for col_name, _width in columns:
            table.add_column(col_name, key=col_name.lower().rstrip("*"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/chain_table.py tests/test_widgets_coverage.py
git commit -m "feat: show * suffix on Greek column headers for calculated values

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Wire Greeks Calculation into App

**Files:**
- Modify: `src/tenortui/app.py:40-50` (constructor)
- Modify: `src/tenortui/app.py:262-315` (_load_ticker)
- Modify: `src/tenortui/app.py:317-335` (_load_chain)
- Modify: `src/tenortui/app.py:354-374` (main)

- [ ] **Step 1: Update `TenorTUI.__init__` to accept greeks config**

In `src/tenortui/app.py`, update the constructor:

```python
from tenortui.config import GreeksConfig, SpreadThresholds, load_config

class TenorTUI(App):
    # ...
    def __init__(self, provider, spread_thresholds: SpreadThresholds | None = None,
                 greeks_config: GreeksConfig | None = None):
        super().__init__()
        self._provider = provider
        self._spread_thresholds = spread_thresholds or SpreadThresholds()
        self._greeks_config = greeks_config or GreeksConfig()
        self._current_symbol: str | None = None
        self._current_expiration: str | None = None
        self._current_price: float | None = None
        self._current_dividend_yield: float | None = None
        self._loading_ticker: bool = False
        self._history = load_history()
        # ... rest unchanged
```

- [ ] **Step 2: Update `_load_ticker` to capture dividend_yield and calculate Greeks**

In `_load_ticker`, after line 278 (`ticker_bar.show_quote(quote)`), add:

```python
            self._current_dividend_yield = quote.dividend_yield
```

Then update the inline chain load block (lines 299-304). Replace:

```python
                chain = await asyncio.to_thread(
                    self._provider.get_chain, symbol, expirations[0]
                )
                await chain_table.display_chain(
                    chain, self._current_price, self._spread_thresholds
                )
```

with:

```python
                chain = await asyncio.to_thread(
                    self._provider.get_chain, symbol, expirations[0]
                )
                if self._greeks_config.enabled and not any(
                    c.has_greeks for c in chain.calls + chain.puts
                ):
                    from tenortui.greeks import calculate_chain_greeks
                    await asyncio.to_thread(
                        calculate_chain_greeks,
                        chain=chain,
                        spot=self._current_price,
                        expiration=expirations[0],
                        risk_free_rate=self._greeks_config.risk_free_rate,
                        dividend_yield=self._current_dividend_yield,
                    )
                await chain_table.display_chain(
                    chain, self._current_price, self._spread_thresholds
                )
```

- [ ] **Step 3: Update `_load_chain` to calculate Greeks**

In `_load_chain`, after `get_chain()` returns and before `display_chain()`:

```python
    @work(exclusive=True, group="chain")
    async def _load_chain(self, symbol: str, expiration: str) -> None:
        chain_table = self.query_one(ChainTable)
        chain_table.loading = True

        try:
            chain = await asyncio.to_thread(
                self._provider.get_chain, symbol, expiration
            )
            if self._greeks_config.enabled and not any(
                c.has_greeks for c in chain.calls + chain.puts
            ):
                from tenortui.greeks import calculate_chain_greeks
                await asyncio.to_thread(
                    calculate_chain_greeks,
                    chain=chain,
                    spot=self._current_price,
                    expiration=expiration,
                    risk_free_rate=self._greeks_config.risk_free_rate,
                    dividend_yield=self._current_dividend_yield,
                )
            await chain_table.display_chain(
                chain, self._current_price, self._spread_thresholds
            )
        except ProviderError as e:
            await chain_table.show_message(str(e))

        chain_table.loading = False
        self.query_one(StatusBar).update_refresh_time()
        self._focus_first_table()
```

Apply the same pattern to the inline chain load inside `_load_ticker`.

- [ ] **Step 4: Update `main()` to pass greeks_config**

```python
    app = TenorTUI(
        provider=provider,
        spread_thresholds=config.spread_thresholds,
        greeks_config=config.greeks,
    )
```

- [ ] **Step 5: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 6: Lint and format**

Run: `poetry run ruff check src/ tests/ && poetry run ruff format --check src/ tests/`
Expected: No issues

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/app.py
git commit -m "feat: wire Greeks calculation into app load flow

Closes #9

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: Create Follow-up Issues

**Files:** None (GitHub operations only)

- [ ] **Step 1: Create issue for live risk-free rate API**

```bash
gh issue create \
  --title "Fetch live risk-free rate from Treasury API" \
  --body "## Summary
Fetch the current risk-free rate from a Treasury yields API instead of using the static \`yahoo.greeks.risk_free_rate\` config value.

## Details
- Currently \`risk_free_rate\` defaults to 0.05 and can be overridden in config
- Should fetch current 3-month T-bill rate (e.g., from FRED API or Treasury.gov)
- Cache the rate for the session (no need to re-fetch per chain load)
- Fall back to config value if API is unavailable

## Success Criteria
- [ ] Live rate fetched on app startup
- [ ] Rate cached for session duration
- [ ] Graceful fallback to config default on API failure
- [ ] No user-visible delay from the API call" \
  --label "enhancement" --label "claude"
```

- [ ] **Step 2: Create issue for config help mechanism**

```bash
gh issue create \
  --title "Add help mechanism for YAML configuration options" \
  --body "## Summary
Provide a way for users to discover all available YAML configuration options without reading source code.

## Details
- Users should be able to see the full set of config options, their types, defaults, and descriptions
- Could be a CLI flag (\`tenortui --config-help\`), a command palette command, or generated docs
- Should cover all providers and their settings

## Success Criteria
- [ ] All config options are documented with types and defaults
- [ ] Users can access this information from the CLI or app
- [ ] Documentation stays in sync with actual config parsing code" \
  --label "enhancement" --label "claude"
```

- [ ] **Step 3: Commit** (nothing to commit — GitHub-only operations)
