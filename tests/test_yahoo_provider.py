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

    def test_returns_quote_with_fundamentals(self):
        info = _load_fixture("yahoo_quote.json")
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("AAPL")
        assert quote.pe_ratio == 31.35
        assert quote.eps == 7.91
        assert quote.dividend_yield == 0.42
        assert quote.earnings_date is not None
        assert quote.moving_avg_50d == 261.13
        assert quote.moving_avg_200d == 246.82

    def test_earnings_date_formatted(self):
        info = _load_fixture("yahoo_quote.json")
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("AAPL")
        # earningsTimestamp 1769720400 = Jan 29 2026 UTC
        assert quote.earnings_date == "Jan 29"

    def test_quote_without_fundamentals(self):
        info = {
            "shortName": "Test Corp.",
            "regularMarketPrice": 100.0,
            "regularMarketChange": 0.5,
            "regularMarketChangePercent": 0.5,
            "regularMarketVolume": 1000000,
            "marketCap": 500000000,
        }
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("TEST")
        assert quote.pe_ratio is None
        assert quote.eps is None
        assert quote.earnings_date is None

    def test_nan_fundamentals_become_none(self):
        info = {
            "shortName": "NaN Corp.",
            "regularMarketPrice": 100.0,
            "regularMarketChange": 0.0,
            "regularMarketChangePercent": 0.0,
            "regularMarketVolume": 1000000,
            "marketCap": 500000000,
            "trailingPE": float("nan"),
            "trailingEps": float("nan"),
            "dividendYield": float("nan"),
            "fiftyDayAverage": float("nan"),
            "twoHundredDayAverage": float("nan"),
        }
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("NAN")
        assert quote.pe_ratio is None
        assert quote.eps is None
        assert quote.dividend_yield is None
        assert quote.moving_avg_50d is None
        assert quote.moving_avg_200d is None

    def test_invalid_earnings_timestamp_becomes_none(self):
        info = {
            "shortName": "Bad Earnings Corp.",
            "regularMarketPrice": 100.0,
            "regularMarketChange": 0.0,
            "regularMarketChangePercent": 0.0,
            "regularMarketVolume": 1000000,
            "marketCap": 500000000,
            "earningsTimestamp": "not_a_timestamp",
        }
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker", return_value=_mock_ticker(info)
        ):
            quote = provider.get_quote("BAD")
        assert quote.earnings_date is None

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
