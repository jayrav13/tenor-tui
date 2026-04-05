"""Tests for enhanced ChainTable: filtering, sorting, visual highlights,
sort toggle, sort indicators, and earnings warnings."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import DataTable

from tenortui.chain_filters import ChainFilters, parse_filter_command
from tenortui.models import OptionContract, OptionsChain
from tenortui.widgets.chain_table import ChainTable


class WidgetTestApp(App):
    def __init__(self, widget):
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


def _make_contract(
    strike,
    option_type="call",
    volume=100,
    open_interest=500,
    iv=0.30,
    delta=None,
    gamma=None,
    theta=None,
    vega=None,
    rho=None,
):
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
        gamma=gamma,
        theta=theta,
        vega=vega,
        rho=rho,
    )


def _make_chain(calls=None, puts=None):
    return OptionsChain(
        symbol="TEST",
        expiration="2026-04-17",
        calls=calls or [],
        puts=puts or [],
    )


# ---------------------------------------------------------------------------
# Task 5: Filtering / Sorting integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_table_with_filters():
    """Filters hide zero-volume contracts."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, volume=0),
            _make_contract(110.0, volume=500),
            _make_contract(120.0, volume=200),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=1))
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # The zero-volume contract should be filtered out.
        # We expect 2 data rows + 1 ATM row = 3 total rows.
        assert calls_table.row_count == 3


@pytest.mark.asyncio
async def test_chain_table_sort_by_volume():
    """Sorting by volume works and suppresses ATM divider."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, volume=50),
            _make_contract(110.0, volume=500),
            _make_contract(120.0, volume=200),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=True)
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # No ATM divider when sorted by non-strike column
        assert calls_table.row_count == 3


@pytest.mark.asyncio
async def test_chain_table_filter_clear():
    """clear_filters resets to no filtering."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, volume=0),
            _make_contract(110.0, volume=500),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=1))
        await widget.display_chain(chain, current_price=105.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # 1 contract + ATM row = 2
        assert calls_table.row_count == 2

        # Clear filters and re-render
        widget.clear_filters()
        await widget.display_chain(chain, current_price=105.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # 2 contracts + ATM row = 3
        assert calls_table.row_count == 3


@pytest.mark.asyncio
async def test_chain_table_earnings_warning():
    """Section label shows earnings warning when earnings_date is set."""
    chain = _make_chain(calls=[_make_contract(100.0)])
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=95.0, earnings_date="Apr 25")
        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "Earnings: Apr 25" in calls_label


@pytest.mark.asyncio
async def test_chain_table_filter_count_in_label():
    """Section label shows filter count when filters are active."""
    chain = _make_chain(calls=[_make_contract(100.0, volume=100)])
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=10, min_oi=5))
        await widget.display_chain(chain, current_price=95.0)
        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "(2 filters)" in calls_label


# ---------------------------------------------------------------------------
# Task 6: Visual Highlights
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_table_iv_color_applied():
    """Renders without error with varying IVs (IV color coding applied)."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, iv=0.10),
            _make_contract(110.0, iv=0.50),
            _make_contract(120.0, iv=0.90),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        # Just verify it rendered without error and has rows
        assert tables.first().row_count > 0


@pytest.mark.asyncio
async def test_chain_table_high_volume_bold():
    """Renders without error with high-volume contracts (bold applied)."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, volume=10),
            _make_contract(110.0, volume=10),
            _make_contract(120.0, volume=10000),  # far above median
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        assert tables.first().row_count > 0


@pytest.mark.asyncio
async def test_chain_table_delta_color_applied():
    """Renders with greeks present and delta color applied."""
    chain = _make_chain(
        calls=[
            _make_contract(
                100.0, delta=0.8, gamma=0.02, theta=-0.05, vega=0.1, rho=0.01
            ),
            _make_contract(
                110.0, delta=0.5, gamma=0.04, theta=-0.03, vega=0.15, rho=0.02
            ),
            _make_contract(
                120.0, delta=0.2, gamma=0.01, theta=-0.01, vega=0.05, rho=0.005
            ),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=115.0)
        tables = widget.query(DataTable)
        assert tables.first().row_count > 0


# ---------------------------------------------------------------------------
# Task 7: Wire Filter Commands in App (parse_filter_command integration)
# ---------------------------------------------------------------------------


def test_parse_filter_command_volume_integration():
    """parse_filter_command returns correct ChainFilters for volume filter."""
    result = parse_filter_command("vol > 100")
    assert result is not None
    assert result.min_volume == 101
    assert result.is_active


def test_parse_filter_command_clear_integration():
    """parse_filter_command returns None for 'clear'."""
    result = parse_filter_command("clear")
    assert result is None


# ---------------------------------------------------------------------------
# Task 8: Column Header Sort Toggle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_table_sort_toggle():
    """Verify set_sort state changes cycle correctly."""
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        # Initially no sort
        assert widget._sort_column is None
        assert widget._sort_reverse is False

        # Set sort ascending
        widget.set_sort("vol", reverse=False)
        assert widget._sort_column == "vol"
        assert widget._sort_reverse is False

        # Set sort descending
        widget.set_sort("vol", reverse=True)
        assert widget._sort_column == "vol"
        assert widget._sort_reverse is True

        # Clear sort
        widget.set_sort(None)
        assert widget._sort_column is None
        assert widget._sort_reverse is False


@pytest.mark.asyncio
async def test_chain_table_header_selected_toggle():
    """on_data_table_header_selected toggles sort state."""
    chain = _make_chain(
        calls=[
            _make_contract(100.0, volume=50),
            _make_contract(110.0, volume=500),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=105.0)
        # Initially no custom sort
        assert widget._sort_column is None

        # Simulate header click on "vol"
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # Find the vol column key
        vol_col = None
        for col in calls_table.columns.values():
            if col.key.value == "vol":
                vol_col = col
                break
        assert vol_col is not None

        # First click -> ascending
        event = DataTable.HeaderSelected(
            calls_table, vol_col.key, column_index=0, label=vol_col.label
        )
        widget.on_data_table_header_selected(event)
        assert widget._sort_column == "vol"
        assert widget._sort_reverse is False

        # Second click -> descending
        widget.on_data_table_header_selected(event)
        assert widget._sort_column == "vol"
        assert widget._sort_reverse is True

        # Third click -> clear
        widget.on_data_table_header_selected(event)
        assert widget._sort_column is None
        assert widget._sort_reverse is False


# ---------------------------------------------------------------------------
# Task 9: Sort Direction Indicators
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_table_sort_indicator_in_header():
    """Ascending sort shows up-arrow in column header."""
    chain = _make_chain(calls=[_make_contract(100.0)])
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=False)
        await widget.display_chain(chain, current_price=95.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        col_labels = [str(col.label) for col in calls_table.columns.values()]
        vol_labels = [lbl for lbl in col_labels if "Vol" in lbl]
        assert len(vol_labels) == 1
        assert "\u25b2" in vol_labels[0]  # up arrow


@pytest.mark.asyncio
async def test_chain_table_sort_indicator_descending():
    """Descending sort shows down-arrow in column header."""
    chain = _make_chain(calls=[_make_contract(100.0)])
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_sort("vol", reverse=True)
        await widget.display_chain(chain, current_price=95.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        col_labels = [str(col.label) for col in calls_table.columns.values()]
        vol_labels = [lbl for lbl in col_labels if "Vol" in lbl]
        assert len(vol_labels) == 1
        assert "\u25bc" in vol_labels[0]  # down arrow


@pytest.mark.asyncio
async def test_chain_table_no_sort_indicator_when_unsorted():
    """No arrow indicators when sort is not active."""
    chain = _make_chain(calls=[_make_contract(100.0)])
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=95.0)
        tables = widget.query(DataTable)
        calls_table = tables.first()
        col_labels = [str(col.label) for col in calls_table.columns.values()]
        for label in col_labels:
            assert "\u25b2" not in label
            assert "\u25bc" not in label


# ---------------------------------------------------------------------------
# Task 10: Full integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_enhanced_chain_workflow():
    """Integration test: filter + sort + visual highlights all work together."""
    chain = OptionsChain(
        symbol="TEST",
        expiration="2026-04-17",
        calls=[
            _make_contract(100, volume=0, iv=0.10, delta=0.9),
            _make_contract(110, volume=50, iv=0.25, delta=0.5),
            _make_contract(120, volume=1000, iv=0.50, delta=0.1),
        ],
        puts=[
            _make_contract(100, "put", volume=30, iv=0.15, delta=-0.1),
            _make_contract(110, "put", volume=200, iv=0.30, delta=-0.5),
        ],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.set_filters(ChainFilters(min_volume=1))
        widget.set_sort("iv", reverse=True)
        await widget.display_chain(chain, current_price=115.0, earnings_date="Apr 10")
        tables = widget.query(DataTable)
        calls_table = tables.first()
        # Filtered out volume=0, so 2 calls remain.
        # No ATM divider row because sort is active (divider only shown when
        # sorted by strike).
        assert calls_table.row_count == 2

        # Check section label has earnings warning
        labels = widget.query(".section-label")
        calls_label = str(labels.first().render().plain)
        assert "Earnings" in calls_label
