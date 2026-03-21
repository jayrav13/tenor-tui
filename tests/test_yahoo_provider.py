import json
from pathlib import Path
from collections import namedtuple
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from tenortui.providers.yahoo import YahooProvider
from tenortui.exceptions import SymbolNotFoundError
from tenortui.models import Quote, OptionsChain

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_ticker(
    info: dict, options: tuple[str, ...] = (), chain_data: dict | None = None
):
    ticker = MagicMock()
    ticker.info = info
    ticker.options = options

    if chain_data:
        OptionChain = namedtuple("OptionChain", ["calls", "puts"])
        calls_df = pd.DataFrame(chain_data["calls"])
        puts_df = pd.DataFrame(chain_data["puts"])
        ticker.option_chain.return_value = OptionChain(calls=calls_df, puts=puts_df)

    return ticker


class TestYahooProviderGetQuote:
    def test_returns_quote(self):
        info = _load_fixture("yahoo_quote.json")
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("AAPL")
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 213.25
        assert quote.change == 1.42
        assert quote.volume == 54200000

    def test_symbol_not_found(self):
        ticker = MagicMock()
        ticker.info = {"regularMarketPrice": None}
        provider = YahooProvider()
        with patch("tenortui.providers.yahoo.yf.Ticker", return_value=ticker):
            with pytest.raises(SymbolNotFoundError):
                provider.get_quote("FAKESYMBOL")


class TestYahooProviderGetExpirations:
    def test_returns_expirations(self):
        expirations = ("2026-03-21", "2026-03-28", "2026-04-04")
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            return_value=_mock_ticker({}, options=expirations),
        ):
            result = provider.get_expirations("AAPL")
        assert result == ["2026-03-21", "2026-03-28", "2026-04-04"]


class TestYahooProviderGetChain:
    def test_returns_chain(self):
        chain_data = _load_fixture("yahoo_chain.json")
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            return_value=_mock_ticker({}, chain_data=chain_data),
        ):
            chain = provider.get_chain("AAPL", "2026-03-21")
        assert isinstance(chain, OptionsChain)
        assert chain.symbol == "AAPL"
        assert chain.expiration == "2026-03-21"
        assert len(chain.calls) == 2
        assert len(chain.puts) == 1
        assert chain.calls[0].strike == 200.0
        assert chain.calls[0].bid == 14.20
        assert chain.calls[0].delta is None
