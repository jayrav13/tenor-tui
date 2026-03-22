from textual.widget import Widget
from textual.widgets import Static

from tenortui.models import Quote


class FundamentalsBar(Widget):
    DEFAULT_CSS = """
    FundamentalsBar {
        dock: top;
        height: 1;
        background: $surface;
        padding: 0 1;
    }
    FundamentalsBar #fundamentals-display {
        width: 1fr;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.display = False

    def compose(self):
        yield Static("", id="fundamentals-display")

    def show_fundamentals(self, quote: Quote) -> None:
        parts = []
        if quote.pe_ratio is not None:
            parts.append(f"P/E: {quote.pe_ratio:.2f}")
        if quote.eps is not None:
            parts.append(f"EPS: ${quote.eps:.2f}")
        if quote.dividend_yield is not None:
            parts.append(f"Div: {quote.dividend_yield:.2f}%")
        if quote.earnings_date is not None:
            parts.append(f"Earnings: {quote.earnings_date}")
        if quote.moving_avg_50d is not None:
            parts.append(f"50d: ${quote.moving_avg_50d:.2f}")
        if quote.moving_avg_200d is not None:
            parts.append(f"200d: ${quote.moving_avg_200d:.2f}")

        if not parts:
            self.display = False
            return

        self.query_one("#fundamentals-display").update(" | ".join(parts))
        self.display = True

    def hide(self) -> None:
        self.display = False
