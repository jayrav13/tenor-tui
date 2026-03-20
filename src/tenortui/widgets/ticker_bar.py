from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static

from tenortui.models import Quote


class TickerBar(Widget):
    DEFAULT_CSS = """
    TickerBar {
        dock: top;
        height: 3;
        background: $surface;
        padding: 0 1;
    }
    TickerBar Horizontal {
        height: 3;
        align: left middle;
    }
    TickerBar Input {
        width: 12;
        margin: 0 1 0 0;
    }
    TickerBar .quote-info {
        width: 1fr;
        padding: 0 1;
    }
    TickerBar .error-message {
        width: 1fr;
        padding: 0 1;
        color: $error;
    }
    """

    class TickerSubmitted(Message):
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="Ticker...", id="ticker-input")
            yield Static("", id="quote-display", classes="quote-info")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        symbol = event.value.strip().upper()
        if symbol:
            self.post_message(self.TickerSubmitted(symbol))

    def show_quote(self, quote: Quote) -> None:
        change_sign = "+" if quote.change >= 0 else ""
        text = (
            f"{quote.name}  "
            f"${quote.price:.2f}  "
            f"{change_sign}{quote.change:.2f} "
            f"({change_sign}{quote.change_percent:.2f}%)"
        )
        display = self.query_one("#quote-display", Static)
        display.remove_class("error-message")
        display.add_class("quote-info")
        display.update(text)

    def show_error(self, message: str) -> None:
        display = self.query_one("#quote-display", Static)
        display.remove_class("quote-info")
        display.add_class("error-message")
        display.update(message)

    def focus_input(self) -> None:
        self.query_one("#ticker-input", Input).focus()
