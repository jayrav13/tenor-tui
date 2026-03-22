from tenortui.greeks import calculate_european, calculate_intrinsic


class TestIntrinsicTier:
    def test_call_itm(self):
        result = calculate_intrinsic(spot=110.0, strike=100.0, option_type="call")
        assert result["delta"] == 1.0
        assert result["gamma"] == 0.0
        assert result["theta"] == 0.0
        assert result["vega"] == 0.0
        assert result["rho"] == 0.0
        assert result["price"] == 10.0
        assert result["model"] == "intrinsic"

    def test_call_otm(self):
        result = calculate_intrinsic(spot=90.0, strike=100.0, option_type="call")
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_put_itm(self):
        result = calculate_intrinsic(spot=90.0, strike=100.0, option_type="put")
        assert result["delta"] == -1.0
        assert result["price"] == 10.0

    def test_put_otm(self):
        result = calculate_intrinsic(spot=110.0, strike=100.0, option_type="put")
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_call_atm(self):
        result = calculate_intrinsic(spot=100.0, strike=100.0, option_type="call")
        assert result["delta"] == 0.0
        assert result["price"] == 0.0

    def test_put_atm(self):
        result = calculate_intrinsic(spot=100.0, strike=100.0, option_type="put")
        assert result["delta"] == 0.0
        assert result["price"] == 0.0


class TestEuropeanTier:
    """Validated against textbook Black-Scholes values.

    Reference: S=100, K=100, T=1yr, r=0.05, sigma=0.20, q=0
    Expected (Hull, Options Futures & Other Derivatives):
        Call: Delta~0.6368, Gamma~0.0188, Theta~-0.0176/day,
              Vega~0.3752, Rho~0.5323
        Put:  Delta~-0.3632, Rho~-0.4189
    """

    def test_call_atm(self):
        result = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "european"
        assert abs(result["delta"] - 0.6368) < 0.01
        assert abs(result["gamma"] - 0.0188) < 0.01
        assert abs(result["theta"] - (-0.0176)) < 0.01
        assert abs(result["vega"] - 0.3752) < 0.01
        assert abs(result["rho"] - 0.5323) < 0.01

    def test_put_atm(self):
        result = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="put",
        )
        assert result["model"] == "european"
        assert abs(result["delta"] - (-0.3632)) < 0.01
        assert abs(result["rho"] - (-0.4189)) < 0.01

    def test_deep_itm_call(self):
        result = calculate_european(
            spot=150.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["delta"] > 0.95

    def test_deep_otm_call(self):
        result = calculate_european(
            spot=50.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["delta"] < 0.05

    def test_with_dividend_yield(self):
        result = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.02,
            option_type="call",
        )
        no_div = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["delta"] < no_div["delta"]

    def test_short_expiry(self):
        result = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1 / 365,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "european"
        assert abs(result["delta"] - 0.5) < 0.1
