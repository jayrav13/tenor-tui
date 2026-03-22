"""
Client-side Greeks calculation engine.

Three-tier fallback chain:
  1. CRR Binomial American (200-step)
  2. Black-Scholes European (analytic)
  3. Intrinsic value (arithmetic)

Pure Python — no external dependencies.
"""


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
