from tenortui.models import Quote, OptionContract, OptionsChain


class TestQuote:
    def test_create_quote(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
        )
        assert q.symbol == "AAPL"
        assert q.price == 213.25

    def test_quote_market_cap_optional(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=None,
        )
        assert q.market_cap is None


class TestOptionContract:
    def test_mid_property(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=0.81, gamma=0.03, theta=-0.15, vega=0.25, rho=0.10,
        )
        assert c.mid == (14.20 + 14.50) / 2

    def test_mid_with_zero_bid_ask(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00500000",
            option_type="call",
            strike=500.0,
            bid=0.0, ask=0.01,
            last_price=0.01,
            volume=0, open_interest=0,
            implied_volatility=0.0,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        )
        assert c.mid == 0.005

    def test_greeks_optional(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20, ask=14.50,
            last_price=14.35,
            volume=1234, open_interest=8901,
            implied_volatility=0.32,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        )
        assert c.delta is None
        assert c.gamma is None

    def test_has_greeks(self):
        with_greeks = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0, bid=14.20, ask=14.50,
            last_price=14.35, volume=1234, open_interest=8901,
            implied_volatility=0.32,
            delta=0.81, gamma=0.03, theta=-0.15, vega=0.25, rho=0.10,
        )
        without_greeks = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0, bid=14.20, ask=14.50,
            last_price=14.35, volume=1234, open_interest=8901,
            implied_volatility=0.32,
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        )
        assert with_greeks.has_greeks is True
        assert without_greeks.has_greeks is False


class TestOptionsChain:
    def test_create_chain(self):
        chain = OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=[], puts=[])
        assert chain.symbol == "AAPL"
        assert chain.expiration == "2026-03-21"
        assert chain.calls == []
        assert chain.puts == []
