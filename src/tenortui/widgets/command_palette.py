from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static


class CommandPalette(Widget):
    DEFAULT_CSS = """
    CommandPalette {
        dock: bottom;
        height: 3;
        display: none;
        background: $surface;
    }
    CommandPalette Horizontal {
        height: 3;
        align: left middle;
    }
    CommandPalette .cmd-prefix {
        width: 2;
        color: $accent;
        padding: 1 0 0 1;
    }
    CommandPalette Input {
        width: 1fr;
        border: none;
    }
    """

    class CommandSubmitted(Message):
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(":", classes="cmd-prefix")
            yield Input(id="cmd-input")

    def open(self) -> None:
        self.display = True
        cmd_input = self.query_one("#cmd-input", Input)
        cmd_input.value = ""
        self.call_after_refresh(cmd_input.focus)

    def close(self) -> None:
        self.display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if command:
            self.post_message(self.CommandSubmitted(command))
        self.close()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.close()
            event.prevent_default()
            event.stop()
