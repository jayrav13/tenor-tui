"""Regression tests for #63: dividend yield units and ordering for Greeks.

`Quote.dividend_yield` is a decimal fraction (0.0042 == 0.42%). Yahoo returns
`dividendYield` as a percent, so the Yahoo boundary must divide by 100, and
the app must pass the post-fundamentals yield to `calculate_chain_greeks`.
"""

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from tenortui.app import TenorTUI
from tenortui.config import GreeksConfig
from tenortui.watchlists import Watchlist, WatchlistData


def _patch_app_seams(monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
    )
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: [])
    monkeypatch.setattr("tenortui.app.get_risk_free_rate", lambda **kw: (0.05, False))


def _spy_greeks(monkeypatch):
    calls = []

    def spy(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("tenortui.greeks.calculate_chain_greeks", spy)
    return calls


async def _q_passed_to_greeks(monkeypatch, provider, quote):
    calls = _spy_greeks(monkeypatch)
    provider._quote = quote
    app = TenorTUI(provider=provider, greeks_config=GreeksConfig(enabled=True))
    async with app.run_test():
        app._load_ticker("AAPL")
        await app.workers.wait_for_complete()
    assert calls, "calculate_chain_greeks was not called"
    return calls[-1]["dividend_yield"]


@pytest.mark.asyncio
async def test_yahoo_percent_yield_converted_to_decimal_for_greeks(
    sample_quote, fake_provider, monkeypatch
):
    """Real fetch_fundamentals with Yahoo's percent 0.42 gives q=0.0042."""
    _patch_app_seams(monkeypatch)
    ticker = MagicMock()
    ticker.info = {"dividendYield": 0.42}
    monkeypatch.setattr("tenortui.providers.yahoo.yf.Ticker", lambda symbol: ticker)
    quote = replace(sample_quote, dividend_yield=None)
    q = await _q_passed_to_greeks(monkeypatch, fake_provider, quote)
    assert q == pytest.approx(0.0042)


@pytest.mark.asyncio
async def test_tradier_uses_fundamentals_yield_for_greeks(
    sample_quote, fake_provider, monkeypatch
):
    """Provider quote has no yield; the fundamentals yield reaches Greeks."""
    _patch_app_seams(monkeypatch)

    def fake_fundamentals(quote):
        quote.dividend_yield = 0.0042
        return quote

    monkeypatch.setattr("tenortui.app.fetch_fundamentals", fake_fundamentals)
    quote = replace(sample_quote, dividend_yield=None)
    q = await _q_passed_to_greeks(monkeypatch, fake_provider, quote)
    assert q == pytest.approx(0.0042)


@pytest.mark.asyncio
async def test_provider_yield_kept_when_fundamentals_have_none(
    sample_quote, fake_provider, monkeypatch
):
    """If fundamentals return no yield, the provider's yield is still used."""
    _patch_app_seams(monkeypatch)

    def fake_fundamentals(quote):
        quote.dividend_yield = None
        return quote

    monkeypatch.setattr("tenortui.app.fetch_fundamentals", fake_fundamentals)
    quote = replace(sample_quote, dividend_yield=0.0042)
    q = await _q_passed_to_greeks(monkeypatch, fake_provider, quote)
    assert q == pytest.approx(0.0042)
