"""Tests to improve provider coverage — error paths, edge cases."""

from unittest.mock import patch, MagicMock

import pytest
import requests as req

from tenortui.exceptions import ProviderError
from tenortui.providers.yahoo import YahooProvider, batch_quotes
from tenortui.providers.tradier import TradierProvider


# --- Yahoo provider error paths ---


class TestYahooProviderErrors:
    def test_get_quote_exception(self):
        """Yahoo get_quote wraps exceptions in ProviderError."""
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            side_effect=Exception("network error"),
        ):
            with pytest.raises(ProviderError, match="Failed to fetch quote"):
                provider.get_quote("AAPL")

    def test_get_expirations_exception(self):
        """Yahoo get_expirations wraps exceptions in ProviderError."""
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            side_effect=Exception("network error"),
        ):
            with pytest.raises(ProviderError, match="Failed to fetch expirations"):
                provider.get_expirations("AAPL")

    def test_get_chain_exception(self):
        """Yahoo get_chain wraps exceptions in ProviderError."""
        provider = YahooProvider()
        with patch(
            "tenortui.providers.yahoo.yf.Ticker",
            side_effect=Exception("network error"),
        ):
            with pytest.raises(ProviderError, match="Failed to fetch chain"):
                provider.get_chain("AAPL", "2026-03-21")


# --- Batch quotes edge cases ---


class TestBatchQuotesEdgeCases:
    def test_ticker_none_in_tickers_dict(self):
        """batch_quotes skips symbols where ticker is None."""
        mock_tickers = MagicMock()
        mock_tickers.tickers = {"AAPL": None, "MSFT": None}
        with patch("tenortui.providers.yahoo.yf.Tickers", return_value=mock_tickers):
            result = batch_quotes(["AAPL", "MSFT"])
        assert result == []

    def test_ticker_info_raises_exception(self):
        """batch_quotes skips symbols where .info raises."""
        ticker_mock = MagicMock()
        ticker_mock.info.__getitem__ = MagicMock(side_effect=Exception("info failed"))
        type(ticker_mock).info = property(
            lambda self: (_ for _ in ()).throw(Exception("info failed"))
        )

        mock_tickers = MagicMock()
        mock_tickers.tickers = {"AAPL": ticker_mock}
        with patch("tenortui.providers.yahoo.yf.Tickers", return_value=mock_tickers):
            result = batch_quotes(["AAPL"])
        assert result == []

    def test_ticker_missing_market_price(self):
        """batch_quotes skips symbols with no regularMarketPrice."""
        ticker_mock = MagicMock()
        ticker_mock.info = {"regularMarketPrice": None, "shortName": "Apple"}

        mock_tickers = MagicMock()
        mock_tickers.tickers = {"AAPL": ticker_mock}
        with patch("tenortui.providers.yahoo.yf.Tickers", return_value=mock_tickers):
            result = batch_quotes(["AAPL"])
        assert result == []


# --- Tradier provider error paths ---


class TestTradierProviderErrors:
    def test_get_request_exception(self):
        """Tradier _get wraps RequestException in ProviderError."""
        provider = TradierProvider(api_key="test", sandbox=False)
        with patch(
            "tenortui.providers.tradier.requests.get",
            side_effect=req.exceptions.ConnectionError("connection refused"),
        ):
            with pytest.raises(ProviderError, match="Tradier API error"):
                provider.get_quote("AAPL")

    def test_get_http_error(self):
        """Tradier _get handles HTTP error status codes."""
        resp = MagicMock()
        resp.raise_for_status.side_effect = req.exceptions.HTTPError("401 Unauthorized")
        provider = TradierProvider(api_key="bad-key", sandbox=False)
        with patch("tenortui.providers.tradier.requests.get", return_value=resp):
            with pytest.raises(ProviderError, match="Tradier API error"):
                provider.get_quote("AAPL")

    def test_production_url_default(self):
        """TradierProvider defaults to production URL."""
        provider = TradierProvider(api_key="test")
        assert "sandbox" not in provider._base_url
        assert "api.tradier.com" in provider._base_url


# --- Config edge cases (to push config.py coverage) ---


class TestConfigEdgeCases:
    def test_empty_yaml_file(self, tmp_path):
        """Empty YAML file returns default yahoo config."""
        from tenortui.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_config(config_path=config_file)
        assert config.provider_name == "yahoo"

    def test_yaml_none_content(self, tmp_path):
        """YAML file with only comments returns default yahoo config."""
        from tenortui.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("# just a comment\n")
        config = load_config(config_path=config_file)
        assert config.provider_name == "yahoo"

    def test_non_dict_yaml(self, tmp_path):
        """YAML file with list raises ConfigError."""
        from tenortui.config import load_config
        from tenortui.exceptions import ConfigError

        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigError, match="must be a YAML mapping"):
            load_config(config_path=config_file)

    def test_provider_override_unknown(self, tmp_path):
        """Unknown provider override raises ConfigError."""
        from tenortui.config import load_config
        from tenortui.exceptions import ConfigError

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        with pytest.raises(ConfigError, match="Unknown provider"):
            load_config(config_path=config_file, provider_override="nonexistent")

    def test_provider_config_none_becomes_empty_dict(self, tmp_path):
        """Provider section that's None becomes empty dict."""
        from tenortui.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("default: yahoo\nyahoo:\n")
        config = load_config(config_path=config_file)
        assert config.provider_config == {}
