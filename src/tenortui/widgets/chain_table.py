from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Static

from tenortui.models import OptionContract, OptionsChain

BASE_COLUMNS = [
    ("Strike", 10), ("Bid", 8), ("Ask", 8), ("Mid", 8),
    ("Last", 8), ("Vol", 8), ("OI", 8), ("IV", 8),
]

GREEK_COLUMNS = [
    ("Delta", 8), ("Gamma", 8), ("Theta", 8), ("Vega", 8), ("Rho", 8),
]


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
        container.mount(Static("Search for a ticker to view options chain", classes="no-data"))

    async def display_chain(self, chain: OptionsChain, current_price: float | None = None) -> None:
        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        columns = BASE_COLUMNS + (GREEK_COLUMNS if show_greeks else [])

        container = self.query_one(VerticalScroll)
        await container.remove_children()

        calls_table = DataTable()
        puts_table = DataTable()

        await container.mount(Static("CALLS", classes="section-label"))
        await container.mount(calls_table)
        await container.mount(Static("PUTS", classes="section-label"))
        await container.mount(puts_table)

        calls_atm = self._populate_table(calls_table, columns, chain.calls, current_price)
        puts_atm = self._populate_table(puts_table, columns, chain.puts, current_price)

        # Scroll each table so ATM row is visible with context below
        # Move cursor 5 rows past ATM so ATM sits mid-screen, not at bottom
        if calls_atm is not None:
            target = min(calls_atm + 5, calls_table.row_count - 1)
            calls_table.move_cursor(row=target)
        if puts_atm is not None:
            target = min(puts_atm + 5, puts_table.row_count - 1)
            puts_table.move_cursor(row=target)

    def _populate_table(self, table, columns, contracts, current_price) -> int | None:
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
                f"{contract.mid:.2f}",
                f"{contract.last_price:.2f}",
                f"{contract.volume:,}",
                f"{contract.open_interest:,}",
                f"{contract.implied_volatility:.2%}",
            ]
            if any(col[0] in ("Delta", "Gamma", "Theta", "Vega", "Rho") for col in columns):
                row.extend([
                    f"{contract.delta:.3f}" if contract.delta is not None else "",
                    f"{contract.gamma:.3f}" if contract.gamma is not None else "",
                    f"{contract.theta:.3f}" if contract.theta is not None else "",
                    f"{contract.vega:.3f}" if contract.vega is not None else "",
                    f"{contract.rho:.3f}" if contract.rho is not None else "",
                ])
            table.add_row(*row)
            row_count += 1

        return atm_row_idx

    async def show_message(self, text: str) -> None:
        container = self.query_one(VerticalScroll)
        await container.remove_children()
        await container.mount(Static(text, classes="no-data"))
