from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static, TabbedContent, TabPane


class ExpirySelector(Widget):
    DEFAULT_CSS = """
    ExpirySelector {
        height: auto;
        max-height: 5;
    }
    ExpirySelector TabbedContent {
        height: auto;
        max-height: 5;
    }
    ExpirySelector .no-data {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    class ExpirySelected(Message):
        def __init__(self, expiration: str) -> None:
            self.expiration = expiration
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("Search for a ticker to view options", classes="no-data")

    async def set_expirations(self, expirations: list[str]) -> None:
        for child in list(self.children):
            await child.remove()

        if not expirations:
            await self.mount(Static("No options available", classes="no-data"))
            return

        tabbed = TabbedContent(id="expiry-tabs")
        await self.mount(tabbed)
        for exp in expirations:
            await tabbed.add_pane(TabPane(exp, Static(""), id=f"exp-{exp}"))

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        label = str(event.tab.label)
        self.post_message(self.ExpirySelected(label))

    async def show_message(self, text: str) -> None:
        for child in list(self.children):
            await child.remove()
        await self.mount(Static(text, classes="no-data"))
