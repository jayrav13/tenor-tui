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

    def test_quote_fundamentals_default_none(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
        )
        assert q.pe_ratio is None
        assert q.eps is None
        assert q.dividend_yield is None
        assert q.earnings_date is None
        assert q.moving_avg_50d is None
        assert q.moving_avg_200d is None

    def test_quote_with_fundamentals(self):
        q = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
            market_cap=3_200_000_000_000,
            pe_ratio=28.5,
            eps=6.42,
            dividend_yield=0.42,
            earnings_date="Feb 13",
            moving_avg_50d=261.13,
            moving_avg_200d=246.82,
        )
        assert q.pe_ratio == 28.5
        assert q.eps == 6.42
        assert q.dividend_yield == 0.42
        assert q.earnings_date == "Feb 13"
        assert q.moving_avg_50d == 261.13
        assert q.moving_avg_200d == 246.82


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
            delta=0.81,
            gamma=0.03,
            theta=-0.15,
            vega=0.25,
            rho=0.10,
        )
        assert c.mid == (14.20 + 14.50) / 2

    def test_mid_with_zero_bid_ask(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00500000",
            option_type="call",
            strike=500.0,
            bid=0.0,
            ask=0.01,
            last_price=0.01,
            volume=0,
            open_interest=0,
            implied_volatility=0.0,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert c.mid == 0.005

    def test_greeks_optional(self):
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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert c.delta is None
        assert c.gamma is None

    def test_has_greeks(self):
        with_greeks = OptionContract(
            contract_symbol="AAPL260321C00200000",
            option_type="call",
            strike=200.0,
            bid=14.20,
            ask=14.50,
            last_price=14.35,
            volume=1234,
            open_interest=8901,
            implied_volatility=0.32,
            delta=0.81,
            gamma=0.03,
            theta=-0.15,
            vega=0.25,
            rho=0.10,
        )
        without_greeks = OptionContract(
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
        )
        assert with_greeks.has_greeks is True
        assert without_greeks.has_greeks is False

    def test_spread_percent(self):
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
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        # spread = (14.50 - 14.20) / 14.35 * 100 = 2.09...%
        expected = ((14.50 - 14.20) / ((14.20 + 14.50) / 2)) * 100
        assert abs(c.spread_percent - expected) < 0.001

    def test_spread_percent_zero_mid(self):
        c = OptionContract(
            contract_symbol="AAPL260321C00500000",
            option_type="call",
            strike=500.0,
            bid=0.0,
            ask=0.0,
            last_price=0.0,
            volume=0,
            open_interest=0,
            implied_volatility=0.0,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        assert c.spread_percent == 0.0

    def test_spread_percent_wide(self):
        c = OptionContract(
            contract_symbol="AAPL260321P00200000",
            option_type="put",
            strike=200.0,
            bid=0.10,
            ask=0.50,
            last_price=0.30,
            volume=10,
            open_interest=50,
            implied_volatility=0.50,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        # spread = (0.50 - 0.10) / 0.30 * 100 = 133.33%
        expected = ((0.50 - 0.10) / ((0.10 + 0.50) / 2)) * 100
        assert c.spread_percent > 100.0
        assert abs(c.spread_percent - expected) < 0.01


class TestOptionsChain:
    def test_create_chain(self):
        chain = OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=[], puts=[])
        assert chain.symbol == "AAPL"
        assert chain.expiration == "2026-03-21"
        assert chain.calls == []
        assert chain.puts == []

    def test_greeks_calculated_default_false(self):
        chain = OptionsChain(symbol="AAPL", expiration="2026-03-21", calls=[], puts=[])
        assert chain.greeks_calculated is False

    def test_greeks_calculated_set_true(self):
        chain = OptionsChain(
            symbol="AAPL",
            expiration="2026-03-21",
            calls=[],
            puts=[],
            greeks_calculated=True,
        )
        assert chain.greeks_calculated is True
