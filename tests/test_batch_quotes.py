from unittest.mock import patch, MagicMock

from tenortui.providers.yahoo import batch_quotes


class TestBatchQuotes:
    def test_empty_list_returns_empty(self):
        assert batch_quotes([]) == []

    @patch("tenortui.providers.yahoo.yf")
    def test_returns_quotes_for_valid_symbols(self, mock_yf):
        tickers_mock = MagicMock()
        ticker_aapl = MagicMock()
        ticker_aapl.info = {
            "regularMarketPrice": 213.25,
            "shortName": "Apple Inc.",
            "regularMarketChange": 1.42,
            "regularMarketChangePercent": 0.67,
            "regularMarketVolume": 54200000,
            "marketCap": 3200000000000,
        }
        ticker_msft = MagicMock()
        ticker_msft.info = {
            "regularMarketPrice": 420.50,
            "shortName": "Microsoft Corporation",
            "regularMarketChange": -2.10,
            "regularMarketChangePercent": -0.50,
            "regularMarketVolume": 22000000,
            "marketCap": 3100000000000,
        }
        tickers_mock.tickers = {"AAPL": ticker_aapl, "MSFT": ticker_msft}
        mock_yf.Tickers.return_value = tickers_mock

        results = batch_quotes(["AAPL", "MSFT"])
        assert len(results) == 2
        assert results[0].symbol == "AAPL"
        assert results[0].price == 213.25
        assert results[1].symbol == "MSFT"

    @patch("tenortui.providers.yahoo.yf")
    def test_skips_failed_symbols(self, mock_yf):
        tickers_mock = MagicMock()
        ticker_aapl = MagicMock()
        ticker_aapl.info = {
            "regularMarketPrice": 213.25,
            "shortName": "Apple Inc.",
            "regularMarketChange": 1.42,
            "regularMarketChangePercent": 0.67,
            "regularMarketVolume": 54200000,
            "marketCap": 3200000000000,
        }
        ticker_bad = MagicMock()
        ticker_bad.info = {}
        tickers_mock.tickers = {"AAPL": ticker_aapl, "BAD": ticker_bad}
        mock_yf.Tickers.return_value = tickers_mock

        results = batch_quotes(["AAPL", "BAD"])
        assert len(results) == 1
        assert results[0].symbol == "AAPL"

    @patch("tenortui.providers.yahoo.yf")
    def test_handles_api_failure(self, mock_yf):
        mock_yf.Tickers.side_effect = Exception("network error")
        results = batch_quotes(["AAPL"])
        assert results == []
