from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static


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
    StatusBar .status-keys {
        width: 1fr;
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

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(self._provider_name, classes="status-provider")
            yield Static("Ctrl+R: Refresh | /: Search | q: Quit", classes="status-keys")
            yield Static(self._last_refresh, classes="status-time", id="status-time")

    def update_refresh_time(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self._last_refresh = f"Last: {now}"
        try:
            self.query_one("#status-time", Static).update(self._last_refresh)
        except Exception:
            pass
