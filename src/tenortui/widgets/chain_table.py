from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Static

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
    ) -> None:
        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        columns = BASE_COLUMNS + (GREEK_COLUMNS if show_greeks else [])
        thresholds = spread_thresholds or DEFAULT_SPREAD_THRESHOLDS

        container = self.query_one(VerticalScroll)
        await container.remove_children()

        calls_table = DataTable()
        puts_table = DataTable()

        await container.mount(Static("CALLS", classes="section-label"))
        await container.mount(calls_table)
        await container.mount(Static("PUTS", classes="section-label"))
        await container.mount(puts_table)

        calls_atm = self._populate_table(
            calls_table, columns, chain.calls, current_price, thresholds
        )
        puts_atm = self._populate_table(
            puts_table, columns, chain.puts, current_price, thresholds
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
        self, table, columns, contracts, current_price, thresholds
    ) -> int | None:
        """Populate table and return the ATM row index (or None)."""
        for col_name, _width in columns:
            table.add_column(col_name, key=col_name.lower())

        atm_row_idx = None
        atm_inserted = False
        row_count = 0
        for contract in sorted(contracts, key=lambda c: c.strike):
            if current_price and not atm_inserted and contract.strike > current_price:
                atm_row = ["── ATM ──"] + ["─" * 6] * (len(columns) - 1)
                table.add_row(*atm_row)
                atm_row_idx = row_count
                row_count += 1
                atm_inserted = True

            row = [
                f"{contract.strike:.2f}",
                f"{contract.bid:.2f}",
                f"{contract.ask:.2f}",
                self._format_spread(contract.spread_percent, thresholds),
                f"{contract.mid:.2f}",
                f"{contract.last_price:.2f}",
                f"{contract.volume:,}",
                f"{contract.open_interest:,}",
                f"{contract.implied_volatility:.2%}",
            ]
            if any(
                col[0] in ("Delta", "Gamma", "Theta", "Vega", "Rho") for col in columns
            ):
                row.extend(
                    [
                        f"{contract.delta:.3f}" if contract.delta is not None else "",
                        f"{contract.gamma:.3f}" if contract.gamma is not None else "",
                        f"{contract.theta:.3f}" if contract.theta is not None else "",
                        f"{contract.vega:.3f}" if contract.vega is not None else "",
                        f"{contract.rho:.3f}" if contract.rho is not None else "",
                    ]
                )
            table.add_row(*row)
            row_count += 1

        return atm_row_idx

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
