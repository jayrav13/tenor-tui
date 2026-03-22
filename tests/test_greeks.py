from tenortui.greeks import calculate_intrinsic


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
