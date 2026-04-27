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
