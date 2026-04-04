from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Static

from tenortui.chain_filters import (
    ChainFilters,
    compute_chain_median,
    delta_color,
    filter_contracts,
    is_high_activity,
    iv_color,
    iv_percentile_rank,
    sort_contracts,
)
from tenortui.config import SpreadThresholds
from tenortui.models import OptionsChain

BASE_COLUMNS = [
    ("Strike", 10),
    ("Bid", 8),
    ("Ask", 8),
    ("Spread", 8),
    ("Mid", 8),
    ("Last", 8),
    ("Vol", 8),
    ("OI", 8),
    ("IV", 8),
]

GREEK_COLUMNS = [
    ("Delta", 8),
    ("Gamma", 8),
    ("Theta", 8),
    ("Vega", 8),
    ("Rho", 8),
]

DEFAULT_SPREAD_THRESHOLDS = SpreadThresholds()


class ChainTable(Widget):
    DEFAULT_CSS = """
    ChainTable {
        height: 1fr;
    }
    ChainTable VerticalScroll {
        height: 1fr;
    }
    ChainTable .section-label {
        height: 1;
        text-style: bold;
        padding: 0 1;
        background: $primary-background;
        color: $text;
        text-align: center;
        width: 1fr;
    }
    ChainTable DataTable {
        height: auto;
        max-height: 50%;
    }
    ChainTable .no-data {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._filters: ChainFilters = ChainFilters()
        self._sort_column: str | None = None
        self._sort_reverse: bool = False
        self._last_chain: OptionsChain | None = None
        self._last_price: float | None = None
        self._last_thresholds: SpreadThresholds | None = None
        self._last_earnings_date: str | None = None

    def set_filters(self, filters: ChainFilters) -> None:
        """Set the active chain filters."""
        self._filters = filters

    def clear_filters(self) -> None:
        """Reset all filters to defaults."""
        self._filters = ChainFilters()

    def set_sort(self, column: str | None, reverse: bool = False) -> None:
        """Set the sort column and direction."""
        self._sort_column = column
        self._sort_reverse = reverse

    def compose(self) -> ComposeResult:
        yield VerticalScroll()

    def on_mount(self) -> None:
        container = self.query_one(VerticalScroll)
        container.mount(
            Static("Search for a ticker to view options chain", classes="no-data")
        )

    async def display_chain(
        self,
        chain: OptionsChain,
        current_price: float | None = None,
        spread_thresholds: SpreadThresholds | None = None,
        earnings_date: str | None = None,
    ) -> None:
        # Store params for re-rendering on sort/filter change
        self._last_chain = chain
        self._last_price = current_price
        self._last_thresholds = spread_thresholds
        self._last_earnings_date = earnings_date

        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        if show_greeks and chain.greeks_calculated:
            greek_cols = [
                ("Delta*", 8),
                ("Gamma*", 8),
                ("Theta*", 8),
                ("Vega*", 8),
                ("Rho*", 8),
            ]
        else:
            greek_cols = GREEK_COLUMNS
        columns = BASE_COLUMNS + (greek_cols if show_greeks else [])
        thresholds = spread_thresholds or DEFAULT_SPREAD_THRESHOLDS

        container = self.query_one(VerticalScroll)
        await container.remove_children()

        calls_table = DataTable()
        puts_table = DataTable()

        # Build section labels
        calls_label = "CALLS"
        puts_label = "PUTS"
        if earnings_date:
            calls_label = f"CALLS \u26a0 Earnings: {earnings_date}"
            puts_label = f"PUTS \u26a0 Earnings: {earnings_date}"
        if self._filters.is_active:
            count = self._filters.active_count
            calls_label += f" ({count} filter{'s' if count != 1 else ''})"
            puts_label += f" ({count} filter{'s' if count != 1 else ''})"

        await container.mount(Static(calls_label, classes="section-label"))
        await container.mount(calls_table)
        await container.mount(Static(puts_label, classes="section-label"))
        await container.mount(puts_table)

        calls_atm = self._populate_table(
            calls_table, columns, chain.calls, current_price, thresholds, side="call"
        )
        puts_atm = self._populate_table(
            puts_table, columns, chain.puts, current_price, thresholds, side="put"
        )

        # Place cursor on ATM row, then center it in the viewport after render
        if calls_atm is not None:
            calls_table.move_cursor(row=calls_atm)
            self._center_on_row(calls_table, calls_atm)
        if puts_atm is not None:
            puts_table.move_cursor(row=puts_atm)
            self._center_on_row(puts_table, puts_atm)

    def _format_spread(self, spread_pct: float, thresholds: SpreadThresholds) -> Text:
        """Format spread percentage with color based on thresholds."""
        if spread_pct < thresholds.tight:
            color = "green"
        elif spread_pct < thresholds.moderate:
            color = "yellow"
        else:
            color = "red"
        return Text(f"{spread_pct:.1f}%", style=color)

    def _populate_table(
        self, table, columns, contracts, current_price, thresholds, side: str = "call"
    ) -> int | None:
        """Populate table and return the ATM row index (or None)."""
        # Apply filtering
        filtered = filter_contracts(
            contracts, self._filters, current_price=current_price, side=side
        )

        # Apply sorting
        if self._sort_column is not None:
            sorted_contracts = sort_contracts(
                filtered, self._sort_column, self._sort_reverse
            )
        else:
            sorted_contracts = sort_contracts(filtered, "strike", reverse=False)

        # Add columns with sort indicators
        for col_name, _width in columns:
            col_key = col_name.lower().rstrip("*")
            label = col_name
            if self._sort_column == col_key:
                arrow = "\u25b2" if not self._sort_reverse else "\u25bc"
                label = f"{col_name} {arrow}"
            table.add_column(label, key=col_key)

        # Compute visual highlight stats
        all_ivs = [c.implied_volatility for c in sorted_contracts]
        median_vol = compute_chain_median([float(c.volume) for c in sorted_contracts])
        median_oi = compute_chain_median(
            [float(c.open_interest) for c in sorted_contracts]
        )

        atm_row_idx = None
        atm_inserted = False
        row_count = 0
        # Only insert ATM divider when sorted by strike (default)
        insert_atm = self._sort_column is None

        for contract in sorted_contracts:
            if (
                insert_atm
                and current_price
                and not atm_inserted
                and contract.strike > current_price
            ):
                atm_row = ["── ATM ──"] + ["─" * 6] * (len(columns) - 1)
                table.add_row(*atm_row)
                atm_row_idx = row_count
                row_count += 1
                atm_inserted = True

            # Build IV cell with color
            iv_pct = iv_percentile_rank(contract.implied_volatility, all_ivs)
            iv_cell = Text(
                f"{contract.implied_volatility:.2%}",
                style=iv_color(iv_pct),
            )

            # Build Vol cell with bold for high activity
            if is_high_activity(float(contract.volume), median_vol):
                vol_cell = Text(f"{contract.volume:,}", style="bold")
            else:
                vol_cell = f"{contract.volume:,}"

            # Build OI cell with bold for high activity
            if is_high_activity(float(contract.open_interest), median_oi):
                oi_cell = Text(f"{contract.open_interest:,}", style="bold")
            else:
                oi_cell = f"{contract.open_interest:,}"

            row = [
                f"{contract.strike:.2f}",
                f"{contract.bid:.2f}",
                f"{contract.ask:.2f}",
                self._format_spread(contract.spread_percent, thresholds),
                f"{contract.mid:.2f}",
                f"{contract.last_price:.2f}",
                vol_cell,
                oi_cell,
                iv_cell,
            ]
            if any(
                col[0].rstrip("*") in ("Delta", "Gamma", "Theta", "Vega", "Rho")
                for col in columns
            ):
                # Delta with color
                if contract.delta is not None:
                    delta_cell = Text(
                        f"{contract.delta:.3f}",
                        style=delta_color(contract.delta),
                    )
                else:
                    delta_cell = ""
                row.extend(
                    [
                        delta_cell,
                        f"{contract.gamma:.3f}" if contract.gamma is not None else "",
                        f"{contract.theta:.3f}" if contract.theta is not None else "",
                        f"{contract.vega:.3f}" if contract.vega is not None else "",
                        f"{contract.rho:.3f}" if contract.rho is not None else "",
                    ]
                )
            table.add_row(*row)
            row_count += 1

        return atm_row_idx

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Toggle sort on column header click."""
        col_key = event.column_key.value
        if self._sort_column == col_key and not self._sort_reverse:
            self._sort_reverse = True
        elif self._sort_column == col_key and self._sort_reverse:
            self._sort_column = None
            self._sort_reverse = False
        else:
            self._sort_column = col_key
            self._sort_reverse = False
        if self._last_chain is not None:
            import asyncio

            asyncio.ensure_future(
                self.display_chain(
                    self._last_chain,
                    self._last_price,
                    self._last_thresholds,
                    earnings_date=self._last_earnings_date,
                )
            )

    def _center_on_row(self, table: DataTable, row_idx: int) -> None:
        """Scroll so the given row is centered in the table's viewport."""

        def _do_center():
            viewport_h = table.scrollable_content_region.height
            if viewport_h > 0:
                # Each row is 1 unit; +1 accounts for the header row
                target_y = max(0, (row_idx + 1) - viewport_h // 2)
                table.scroll_to(0, target_y, animate=False)

        self.call_after_refresh(_do_center)

    async def show_message(self, text: str) -> None:
        container = self.query_one(VerticalScroll)
        await container.remove_children()
        await container.mount(Static(text, classes="no-data"))
