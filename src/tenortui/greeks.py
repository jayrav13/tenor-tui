"""
Client-side Greeks calculation engine.

Three-tier fallback chain:
  1. CRR Binomial American (200-step)
  2. Black-Scholes European (analytic)
  3. Intrinsic value (arithmetic)

Pure Python — no external dependencies.
"""

import math


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


def _norm_cdf(x: float) -> float:
    """Cumulative standard normal distribution via math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def calculate_european(
    spot: float,
    strike: float,
    T: float,
    r: float,
    sigma: float,
    q: float,
    option_type: str,
) -> dict:
    """Tier 2: Analytic Black-Scholes-Merton European engine."""
    sqrt_T = math.sqrt(T)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * T) / (
        sigma * sqrt_T
    )
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
        - r
        * strike
        * exp_rT
        * _norm_cdf(d2 if option_type == "call" else -d2)
        * (1.0 if option_type == "call" else -1.0)
        + q
        * spot
        * exp_qT
        * _norm_cdf(d1 if option_type == "call" else -d1)
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


def _american_price(
    spot: float,
    strike: float,
    T: float,
    r: float,
    sigma: float,
    q: float,
    is_call: bool,
    steps: int,
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


def calculate_american(
    spot: float,
    strike: float,
    T: float,
    r: float,
    sigma: float,
    q: float,
    option_type: str,
    steps: int = 200,
) -> dict:
    """Tier 1: CRR Binomial American engine."""
    dt = T / steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
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
        price_t1 = _american_price(
            spot, strike, T - dt_bump, r, sigma, q, is_call, steps
        )
        theta = price_t1 - price  # already per-day since we bumped by 1 day
    else:
        theta = 0.0

    # Vega via finite difference: bump sigma by 0.01
    dsigma = 0.01
    price_up_vol = _american_price(
        spot, strike, T, r, sigma + dsigma, q, is_call, steps
    )
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
