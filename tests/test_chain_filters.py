"""Tests for chain_filters module: filtering, sorting, command parsing, visual helpers."""

from tenortui.chain_filters import (
    ChainFilters,
    filter_contracts,
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
