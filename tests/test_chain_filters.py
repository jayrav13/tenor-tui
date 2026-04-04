"""Tests for chain_filters module: filtering, sorting, command parsing, visual helpers."""

from tenortui.chain_filters import (
    ChainFilters,
    SORT_KEYS,
    filter_contracts,
    sort_contracts,
)
from tenortui.models import OptionContract


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_contract(
    strike: float,
    option_type: str = "call",
    volume: int = 100,
    open_interest: int = 500,
    iv: float = 0.30,
    delta: float | None = None,
) -> OptionContract:
    return OptionContract(
        contract_symbol=f"TEST{strike}{option_type[0].upper()}",
        option_type=option_type,
        strike=strike,
        bid=1.0,
        ask=1.5,
        last_price=1.25,
        volume=volume,
        open_interest=open_interest,
        implied_volatility=iv,
        delta=delta,
        gamma=0.05 if delta is not None else None,
        theta=-0.03 if delta is not None else None,
        vega=0.15 if delta is not None else None,
        rho=0.01 if delta is not None else None,
    )


# ===========================================================================
# Task 1: TestFilterContracts
# ===========================================================================


class TestFilterContracts:
    def test_no_filters_returns_all(self):
        contracts = [_make_contract(100), _make_contract(110), _make_contract(120)]
        result = filter_contracts(contracts, ChainFilters())
        assert result == contracts

    def test_min_volume_hides_zero_volume(self):
        contracts = [
            _make_contract(100, volume=0),
            _make_contract(110, volume=50),
            _make_contract(120, volume=200),
        ]
        result = filter_contracts(contracts, ChainFilters(min_volume=1))
        strikes = [c.strike for c in result]
        assert 100 not in strikes
        assert 110 in strikes
        assert 120 in strikes

    def test_min_volume_hides_low_volume(self):
        contracts = [
            _make_contract(100, volume=10),
            _make_contract(110, volume=100),
            _make_contract(120, volume=200),
        ]
        result = filter_contracts(contracts, ChainFilters(min_volume=100))
        strikes = [c.strike for c in result]
        assert 100 not in strikes
        assert 110 in strikes
        assert 120 in strikes

    def test_moneyness_itm_calls(self):
        # For calls, ITM means strike < current_price
        contracts = [
            _make_contract(90, option_type="call"),  # ITM (strike < 100)
            _make_contract(100, option_type="call"),  # ATM
            _make_contract(110, option_type="call"),  # OTM
        ]
        result = filter_contracts(
            contracts, ChainFilters(moneyness="itm"), current_price=100, side="call"
        )
        strikes = [c.strike for c in result]
        assert 90 in strikes
        assert 100 not in strikes
        assert 110 not in strikes

    def test_moneyness_itm_puts(self):
        # For puts, ITM means strike > current_price
        contracts = [
            _make_contract(90, option_type="put"),  # OTM
            _make_contract(100, option_type="put"),  # ATM
            _make_contract(110, option_type="put"),  # ITM (strike > 100)
        ]
        result = filter_contracts(
            contracts, ChainFilters(moneyness="itm"), current_price=100, side="put"
        )
        strikes = [c.strike for c in result]
        assert 90 not in strikes
        assert 100 not in strikes
        assert 110 in strikes

    def test_moneyness_otm_calls(self):
        contracts = [
            _make_contract(90, option_type="call"),  # ITM
            _make_contract(100, option_type="call"),  # ATM
            _make_contract(110, option_type="call"),  # OTM
        ]
        result = filter_contracts(
            contracts, ChainFilters(moneyness="otm"), current_price=100, side="call"
        )
        strikes = [c.strike for c in result]
        assert 90 not in strikes
        assert 100 not in strikes
        assert 110 in strikes

    def test_moneyness_otm_puts(self):
        contracts = [
            _make_contract(90, option_type="put"),  # OTM (strike < price)
            _make_contract(100, option_type="put"),  # ATM
            _make_contract(110, option_type="put"),  # ITM
        ]
        result = filter_contracts(
            contracts, ChainFilters(moneyness="otm"), current_price=100, side="put"
        )
        strikes = [c.strike for c in result]
        assert 90 in strikes
        assert 100 not in strikes
        assert 110 not in strikes

    def test_min_delta_filters_out_low_abs_delta(self):
        contracts = [
            _make_contract(100, delta=0.10),
            _make_contract(110, delta=0.30),
            _make_contract(120, delta=0.70),
        ]
        result = filter_contracts(contracts, ChainFilters(min_delta=0.25))
        strikes = [c.strike for c in result]
        assert 100 not in strikes
        assert 110 in strikes
        assert 120 in strikes

    def test_max_delta_filters_out_high_abs_delta(self):
        contracts = [
            _make_contract(100, delta=0.10),
            _make_contract(110, delta=0.50),
            _make_contract(120, delta=0.90),
        ]
        result = filter_contracts(contracts, ChainFilters(max_delta=0.60))
        strikes = [c.strike for c in result]
        assert 100 in strikes
        assert 110 in strikes
        assert 120 not in strikes

    def test_delta_range_combined(self):
        contracts = [
            _make_contract(100, delta=0.10),
            _make_contract(110, delta=0.40),
            _make_contract(120, delta=0.80),
        ]
        result = filter_contracts(
            contracts, ChainFilters(min_delta=0.30, max_delta=0.60)
        )
        strikes = [c.strike for c in result]
        assert 100 not in strikes
        assert 110 in strikes
        assert 120 not in strikes

    def test_min_oi_threshold(self):
        contracts = [
            _make_contract(100, open_interest=50),
            _make_contract(110, open_interest=200),
            _make_contract(120, open_interest=1000),
        ]
        result = filter_contracts(contracts, ChainFilters(min_oi=100))
        strikes = [c.strike for c in result]
        assert 100 not in strikes
        assert 110 in strikes
        assert 120 in strikes

    def test_combined_filters(self):
        contracts = [
            _make_contract(90, volume=5, open_interest=50, delta=0.10),
            _make_contract(100, volume=200, open_interest=500, delta=0.50),
            _make_contract(110, volume=150, open_interest=800, delta=0.80),
        ]
        result = filter_contracts(
            contracts,
            ChainFilters(min_volume=100, min_oi=200, min_delta=0.30, max_delta=0.70),
        )
        strikes = [c.strike for c in result]
        assert 90 not in strikes  # fails volume, oi, delta
        assert 100 in strikes  # passes all
        assert 110 not in strikes  # fails max_delta

    def test_delta_filter_skips_none_delta(self):
        contracts = [
            _make_contract(100, delta=None),
            _make_contract(110, delta=0.50),
        ]
        result = filter_contracts(contracts, ChainFilters(min_delta=0.30))
        strikes = [c.strike for c in result]
        # Contract with None delta should be excluded when delta filter is active
        assert 100 not in strikes
        assert 110 in strikes

    def test_chain_filters_is_active_false_when_empty(self):
        f = ChainFilters()
        assert f.is_active is False

    def test_chain_filters_is_active_true_when_any_set(self):
        assert ChainFilters(min_volume=1).is_active is True
        assert ChainFilters(min_oi=1).is_active is True
        assert ChainFilters(min_delta=0.1).is_active is True
        assert ChainFilters(max_delta=0.9).is_active is True
        assert ChainFilters(moneyness="itm").is_active is True

    def test_chain_filters_active_count(self):
        f = ChainFilters(min_volume=1, min_oi=100)
        assert f.active_count == 2

    def test_chain_filters_active_count_zero_when_empty(self):
        assert ChainFilters().active_count == 0


# ===========================================================================
# Task 2: TestSortContracts
# ===========================================================================


class TestSortContracts:
    def test_sort_by_strike_asc(self):
        contracts = [_make_contract(120), _make_contract(100), _make_contract(110)]
        result = sort_contracts(contracts, "strike", reverse=False)
        assert [c.strike for c in result] == [100, 110, 120]

    def test_sort_by_strike_desc(self):
        contracts = [_make_contract(120), _make_contract(100), _make_contract(110)]
        result = sort_contracts(contracts, "strike", reverse=True)
        assert [c.strike for c in result] == [120, 110, 100]

    def test_sort_by_volume(self):
        contracts = [
            _make_contract(100, volume=300),
            _make_contract(110, volume=100),
            _make_contract(120, volume=200),
        ]
        result = sort_contracts(contracts, "vol")
        assert [c.volume for c in result] == [100, 200, 300]

    def test_sort_by_oi(self):
        contracts = [
            _make_contract(100, open_interest=900),
            _make_contract(110, open_interest=100),
            _make_contract(120, open_interest=500),
        ]
        result = sort_contracts(contracts, "oi")
        assert [c.open_interest for c in result] == [100, 500, 900]

    def test_sort_by_iv(self):
        contracts = [
            _make_contract(100, iv=0.50),
            _make_contract(110, iv=0.20),
            _make_contract(120, iv=0.35),
        ]
        result = sort_contracts(contracts, "iv")
        assert [c.implied_volatility for c in result] == [0.20, 0.35, 0.50]

    def test_sort_by_delta(self):
        contracts = [
            _make_contract(100, delta=0.70),
            _make_contract(110, delta=0.30),
            _make_contract(120, delta=0.50),
        ]
        result = sort_contracts(contracts, "delta")
        assert [c.delta for c in result] == [0.30, 0.50, 0.70]

    def test_none_delta_sorts_to_end(self):
        contracts = [
            _make_contract(100, delta=None),
            _make_contract(110, delta=0.50),
            _make_contract(120, delta=0.20),
        ]
        result = sort_contracts(contracts, "delta")
        assert result[-1].strike == 100  # None delta goes to end
        assert result[0].delta == 0.20

    def test_none_column_defaults_to_strike_sort(self):
        contracts = [_make_contract(120), _make_contract(100), _make_contract(110)]
        result = sort_contracts(contracts, None)
        assert [c.strike for c in result] == [100, 110, 120]

    def test_sort_by_bid(self):
        c1 = OptionContract(
            contract_symbol="A",
            option_type="call",
            strike=100,
            bid=3.0,
            ask=3.5,
            last_price=3.2,
            volume=100,
            open_interest=500,
            implied_volatility=0.3,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        c2 = OptionContract(
            contract_symbol="B",
            option_type="call",
            strike=110,
            bid=1.0,
            ask=1.5,
            last_price=1.2,
            volume=100,
            open_interest=500,
            implied_volatility=0.3,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        c3 = OptionContract(
            contract_symbol="C",
            option_type="call",
            strike=120,
            bid=2.0,
            ask=2.5,
            last_price=2.2,
            volume=100,
            open_interest=500,
            implied_volatility=0.3,
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )
        result = sort_contracts([c1, c2, c3], "bid")
        assert [c.bid for c in result] == [1.0, 2.0, 3.0]

    def test_sort_keys_has_expected_columns(self):
        expected = {
            "strike",
            "bid",
            "ask",
            "spread",
            "mid",
            "last",
            "vol",
            "oi",
            "iv",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
        }
        assert expected.issubset(set(SORT_KEYS.keys()))
