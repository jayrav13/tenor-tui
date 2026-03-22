from tenortui.greeks import (
    calculate_american,
    calculate_chain_greeks,
    calculate_european,
    calculate_greeks,
    calculate_intrinsic,
)
from tenortui.models import OptionContract, OptionsChain


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


class TestAmericanTier:
    """CRR binomial should be close to European for no-dividend calls,
    and should price higher than European for puts (early exercise premium)."""

    def test_call_no_dividend_matches_european(self):
        """Without dividends, American call == European call."""
        american = calculate_american(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        european = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert american["model"] == "american"
        assert abs(american["delta"] - european["delta"]) < 0.02
        assert abs(american["price"] - european["price"]) < 0.5

    def test_put_early_exercise_premium(self):
        """American put should be worth >= European put."""
        american = calculate_american(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="put",
        )
        european = calculate_european(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="put",
        )
        assert american["price"] >= european["price"] - 0.01

    def test_deep_itm_put(self):
        american = calculate_american(
            spot=50.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="put",
        )
        assert american["delta"] < -0.9
        assert american["price"] > 45.0

    def test_greeks_have_correct_signs(self):
        call = calculate_american(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert call["delta"] > 0
        assert call["gamma"] > 0
        assert call["theta"] < 0
        assert call["vega"] > 0
        assert call["rho"] > 0

        put = calculate_american(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="put",
        )
        assert put["delta"] < 0
        assert put["gamma"] > 0
        assert put["theta"] < 0
        assert put["vega"] > 0
        assert put["rho"] < 0

    def test_with_dividend_yield(self):
        result = calculate_american(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.02,
            option_type="call",
        )
        assert result["model"] == "american"
        assert result["delta"] > 0


class TestFallbackRouting:
    def test_zero_iv_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0,
            strike=90.0,
            T=1.0,
            r=0.05,
            sigma=0.0,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_negative_iv_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0,
            strike=90.0,
            T=1.0,
            r=0.05,
            sigma=-0.1,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_zero_time_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0,
            strike=90.0,
            T=0.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_negative_time_routes_to_intrinsic(self):
        result = calculate_greeks(
            spot=100.0,
            strike=90.0,
            T=-1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "intrinsic"

    def test_normal_inputs_use_american(self):
        result = calculate_greeks(
            spot=100.0,
            strike=100.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert result["model"] == "american"

    def test_never_raises(self):
        """Even with absurd inputs, should return a result."""
        result = calculate_greeks(
            spot=0.0,
            strike=0.0,
            T=1.0,
            r=0.05,
            sigma=0.20,
            q=0.0,
            option_type="call",
        )
        assert "delta" in result


class TestCalculateChainGreeks:
    def _make_contract(self, strike, option_type="call", iv=0.30):
        return OptionContract(
            contract_symbol=f"TEST{strike}{option_type[0].upper()}",
            option_type=option_type,
            strike=strike,
            bid=5.0,
            ask=5.50,
            last_price=5.25,
            volume=100,
            open_interest=500,
            implied_volatility=iv,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )

    def test_populates_greeks_on_all_contracts(self):
        chain = OptionsChain(
            symbol="TEST",
            expiration="2027-03-21",
            calls=[self._make_contract(100.0), self._make_contract(110.0)],
            puts=[self._make_contract(100.0, "put"), self._make_contract(110.0, "put")],
        )
        calculate_chain_greeks(
            chain=chain,
            spot=105.0,
            expiration="2027-03-21",
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )
        assert chain.greeks_calculated is True
        for contract in chain.calls + chain.puts:
            assert contract.delta is not None
            assert contract.gamma is not None
            assert contract.theta is not None
            assert contract.vega is not None
            assert contract.rho is not None

    def test_call_deltas_positive_put_deltas_negative(self):
        chain = OptionsChain(
            symbol="TEST",
            expiration="2027-03-21",
            calls=[self._make_contract(100.0)],
            puts=[self._make_contract(100.0, "put")],
        )
        calculate_chain_greeks(
            chain=chain,
            spot=105.0,
            expiration="2027-03-21",
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )
        assert chain.calls[0].delta > 0
        assert chain.puts[0].delta < 0

    def test_none_dividend_yield_treated_as_zero(self):
        chain = OptionsChain(
            symbol="TEST",
            expiration="2027-03-21",
            calls=[self._make_contract(100.0)],
            puts=[],
        )
        calculate_chain_greeks(
            chain=chain,
            spot=105.0,
            expiration="2027-03-21",
            risk_free_rate=0.05,
            dividend_yield=None,
        )
        assert chain.calls[0].delta is not None

    def test_expired_chain_uses_intrinsic(self):
        chain = OptionsChain(
            symbol="TEST",
            expiration="2020-01-01",
            calls=[self._make_contract(100.0)],
            puts=[],
        )
        calculate_chain_greeks(
            chain=chain,
            spot=105.0,
            expiration="2020-01-01",
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )
        assert chain.greeks_calculated is True
        assert chain.calls[0].delta == 1.0  # ITM call intrinsic
