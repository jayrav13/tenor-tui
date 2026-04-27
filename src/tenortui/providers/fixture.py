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
                    f"Unknown expiration {expiration!r}; valid: {_AAPL_EXPIRATIONS}"
                )
            return _aapl_chain(expiration)
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
