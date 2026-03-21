from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static

from tenortui.market_hours import MarketState, get_market_state, time_to_next_state


class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
    }
    StatusBar Horizontal {
        width: 1fr;
        height: 1;
    }
    StatusBar .status-provider {
        width: auto;
        padding: 0 1;
        color: $accent;
    }
    StatusBar .status-market {
        width: auto;
        padding: 0 1;
    }
    StatusBar .status-market-open {
        color: $success;
    }
    StatusBar .status-market-pre {
        color: $warning;
    }
    StatusBar .status-market-post {
        color: $warning;
    }
    StatusBar .status-market-closed {
        color: $text-muted;
    }
    StatusBar .status-keys {
        width: 1fr;
        padding: 0 1;
    }
    StatusBar .status-refresh {
        width: auto;
        padding: 0 1;
    }
    StatusBar .status-time {
        width: auto;
        padding: 0 1;
    }
    """

    def __init__(self, provider_name: str = ""):
        super().__init__()
        self._provider_name = provider_name
        self._last_refresh: str = ""
        self._auto_refresh_paused: bool = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(self._provider_name, classes="status-provider")
            yield Static("", classes="status-market", id="status-market")
            yield Static("? Help", classes="status-keys")
            yield Static("", classes="status-refresh", id="status-refresh")
            yield Static(self._last_refresh, classes="status-time", id="status-time")

    def update_market_state(self) -> None:
        """Update the market state display."""
        state = get_market_state()
        mins = time_to_next_state()

        if mins >= 60:
            hours = mins // 60
            remaining_mins = mins % 60
            countdown = f"{hours}h {remaining_mins}m"
        else:
            countdown = f"{mins}m"

        if state == MarketState.REGULAR:
            text = f"Market Open (closes in {countdown})"
            css_class = "status-market-open"
        elif state == MarketState.PRE_MARKET:
            text = f"Pre-Market (opens in {countdown})"
            css_class = "status-market-pre"
        elif state == MarketState.AFTER_HOURS:
            text = f"After-Hours (closes in {countdown})"
            css_class = "status-market-post"
        else:
            text = "Market Closed"
            css_class = "status-market-closed"

        try:
            market_widget = self.query_one("#status-market", Static)
            market_widget.update(text)
            for cls in (
                "status-market-open",
                "status-market-pre",
                "status-market-post",
                "status-market-closed",
            ):
                market_widget.remove_class(cls)
            market_widget.add_class(css_class)
        except Exception:
            pass

    def update_refresh_status(
        self, seconds_until: int | None = None, paused: bool = False
    ) -> None:
        """Update the auto-refresh status display."""
        self._auto_refresh_paused = paused
        try:
            widget = self.query_one("#status-refresh", Static)
            if paused:
                widget.update("⏸ Paused")
            elif seconds_until is not None:
                widget.update(f"↻ {seconds_until}s")
            else:
                widget.update("")
        except Exception:
            pass

    def update_refresh_time(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self._last_refresh = f"Last: {now}"
        try:
            self.query_one("#status-time", Static).update(self._last_refresh)
        except Exception:
            pass
