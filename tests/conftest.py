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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        ),
    ]
    return OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=calls, puts=puts)


@pytest.fixture
def sample_expirations():
    return ["2026-03-21", "2026-03-28", "2026-04-04", "2026-04-17"]


class FakeProvider:
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
