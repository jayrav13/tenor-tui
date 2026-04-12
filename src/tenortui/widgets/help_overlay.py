from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static


KEYBINDINGS = [
    (
        "Navigation",
        [
            ("j / k", "Move down / up in lists and tables"),
            ("h / l", "Switch to previous / next pane"),
            ("g", "Jump to top of list"),
            ("G", "Jump to bottom of list"),
            ("Tab / Shift+Tab", "Next / previous pane"),
        ],
    ),
    (
        "Actions",
        [
            ("/ or s", "Focus search bar"),
            ("r", "Refresh current data"),
            ("Ctrl+P", "Pause / resume auto-refresh"),
            ("Enter", "Select / expand"),
            ("q", "Quit"),
        ],
    ),
    (
        "Panels",
        [
            ("?", "Toggle this help overlay"),
            (":", "Open command palette"),
            (",", "Open settings"),
        ],
    ),
    (
        "Watchlists",
        [
            ("w", "Add ticker/contract to watchlist"),
            ("W", "Open watchlist manager"),
            ("d", "Remove item from watchlist"),
            ("S", "Cycle sort order (default/symbol/price/change/volume)"),
        ],
    ),
]


class HelpOverlay(ModalScreen):
    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }
    HelpOverlay #help-container {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    HelpOverlay .help-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    HelpOverlay .help-section {
        text-style: bold;
        padding: 1 0 0 0;
        color: $text;
    }
    HelpOverlay .help-row {
        padding: 0 0 0 2;
        color: $text-muted;
    }
    HelpOverlay .help-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("question_mark", "dismiss", "Close", show=False),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("g", "scroll_top", "Scroll to top", show=False),
        Binding("G", "scroll_bottom", "Scroll to bottom", show=False),
    ]

    def action_scroll_down(self) -> None:
        self.query_one("#help-container").scroll_relative(y=1)

    def action_scroll_up(self) -> None:
        self.query_one("#help-container").scroll_relative(y=-1)

    def action_scroll_top(self) -> None:
        self.query_one("#help-container").scroll_home()

    def action_scroll_bottom(self) -> None:
        self.query_one("#help-container").scroll_end()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-container"):
            yield Static("Keyboard Shortcuts", classes="help-title")
            for section_name, bindings in KEYBINDINGS:
                yield Static(f"  {section_name}", classes="help-section")
                for key, desc in bindings:
                    yield Static(f"    {key:<20} {desc}", classes="help-row")
            yield Static("Press ? or Esc to close", classes="help-footer")
