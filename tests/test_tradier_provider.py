import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import requests as req
import pytest

from tenortui.providers.tradier import TradierProvider
from tenortui.exceptions import SymbolNotFoundError, ProviderError
from tenortui.models import Quote, OptionsChain

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_response(json_data: dict, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.side_effect = (
        None if status_code == 200 else req.exceptions.HTTPError(f"HTTP {status_code}")
    )
    return resp


class TestTradierProviderGetQuote:
    def test_returns_quote(self):
        data = _load_fixture("tradier_quote.json")
        provider = TradierProvider(api_key="test", sandbox=False)
        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            quote = provider.get_quote("AAPL")
        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.name == "Apple Inc."
        assert quote.price == 213.25
        assert quote.change == 1.42

    def test_symbol_not_found(self):
        data = {"quotes": {"unmatched_symbols": {"symbol": ["FAKESYMBOL"]}}}
        provider = TradierProvider(api_key="test", sandbox=False)
        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            with pytest.raises(SymbolNotFoundError):
                provider.get_quote("FAKESYMBOL")

    def test_sandbox_url(self):
        provider = TradierProvider(api_key="test", sandbox=True)
        assert "sandbox" in provider._base_url


class TestTradierProviderGetExpirations:
    def test_returns_expirations(self):
        data = _load_fixture("tradier_expirations.json")
        provider = TradierProvider(api_key="test", sandbox=False)
        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            result = provider.get_expirations("AAPL")
        assert result == ["2026-03-21", "2026-03-28", "2026-04-04"]


class TestTradierProviderGetChain:
    def test_returns_chain_with_greeks(self):
        data = _load_fixture("tradier_chain.json")
        provider = TradierProvider(api_key="test", sandbox=False)
        with patch("tenortui.providers.tradier.requests.get", return_value=_mock_response(data)):
            chain = provider.get_chain("AAPL", "2026-03-21")
        assert isinstance(chain, OptionsChain)
        assert len(chain.calls) == 1
        assert len(chain.puts) == 1
        assert chain.calls[0].delta == 0.81
        assert chain.calls[0].gamma == 0.03
        assert chain.puts[0].delta == -0.18
