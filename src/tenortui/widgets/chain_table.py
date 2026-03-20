from textual.app import ComposeResult
from textual.containers import Vertical
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
    ChainTable Vertical {
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
        height: 1fr;
    }
    ChainTable .no-data {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="chain-container"):
            yield Static("Search for a ticker to view options chain", classes="no-data")

    async def display_chain(self, chain: OptionsChain, current_price: float | None = None) -> None:
        show_greeks = any(c.has_greeks for c in chain.calls + chain.puts)
        columns = BASE_COLUMNS + (GREEK_COLUMNS if show_greeks else [])

        # Build new container with fresh widgets to avoid duplicate ID issues
        new_container = Vertical(id="chain-container")
        old_container = self.query_one("#chain-container", Vertical)
        await old_container.remove()
        await self.mount(new_container)

        calls_label = Static("CALLS", classes="section-label")
        calls_table = DataTable()
        puts_label = Static("PUTS", classes="section-label")
        puts_table = DataTable()

        await new_container.mount(calls_label)
        await new_container.mount(calls_table)
        await new_container.mount(puts_label)
        await new_container.mount(puts_table)

        self._populate_table(calls_table, columns, chain.calls, current_price)
        self._populate_table(puts_table, columns, chain.puts, current_price)

    def _populate_table(self, table, columns, contracts, current_price):
        for col_name, _width in columns:
            table.add_column(col_name, key=col_name.lower())

        atm_inserted = False
        for contract in sorted(contracts, key=lambda c: c.strike):
            if current_price and not atm_inserted and contract.strike > current_price:
                atm_row = ["── ATM ──"] + ["─" * 6] * (len(columns) - 1)
                table.add_row(*atm_row)
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

    async def show_message(self, text: str) -> None:
        old_container = self.query_one("#chain-container", Vertical)
        await old_container.remove()
        new_container = Vertical(id="chain-container")
        await self.mount(new_container)
        await new_container.mount(Static(text, classes="no-data"))
