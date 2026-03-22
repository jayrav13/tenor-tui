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
