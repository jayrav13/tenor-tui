# Watchlists Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the RecentlyViewed widget with a full watchlist system supporting named watchlists, equity tickers, and options contracts with live quotes.

**Architecture:** New `watchlists.py` data module handles persistence and CRUD operations. `WatchlistPanel` widget replaces `RecentlyViewed` for display. `WatchlistPicker` and `WatchlistManager` modal screens handle adding items and managing watchlists. `app.py` wires everything together with keybindings and quote refresh workers.

**Tech Stack:** Python 3.11+, Textual (TUI framework), pytest + pytest-asyncio

**Spec:** `docs/specs/2026-04-04-watchlists-design.md`

---

### Task 1: Watchlist Data Models and Persistence

**Files:**
- Create: `src/tenortui/watchlists.py`
- Create: `tests/test_watchlists.py`

- [ ] **Step 1: Write failing tests for data models and load/save**

```python
# tests/test_watchlists.py
import json

from tenortui.watchlists import (
    WatchlistItem,
    Watchlist,
    WatchlistData,
    load_watchlists,
    save_watchlists,
)


class TestWatchlistItem:
    def test_equity_item(self):
        item = WatchlistItem(type="equity", symbol="AAPL")
        assert item.type == "equity"
        assert item.symbol == "AAPL"
        assert item.strike is None
        assert item.option_type is None
        assert item.expiration is None

    def test_option_item(self):
        item = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        assert item.type == "option"
        assert item.strike == 180.0
        assert item.option_type == "put"
        assert item.expiration == "2026-04-17"


class TestLoadWatchlists:
    def test_no_file_returns_default(self, tmp_path):
        data = load_watchlists(tmp_path / "watchlists.json")
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"
        assert data.watchlists[0].items == []
        assert data.active_index == 0

    def test_valid_file(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(
            json.dumps(
                {
                    "watchlists": [
                        {
                            "name": "Tech",
                            "items": [{"type": "equity", "symbol": "AAPL"}],
                        }
                    ],
                    "active_index": 0,
                }
            )
        )
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Tech"
        assert len(data.watchlists[0].items) == 1
        assert data.watchlists[0].items[0].symbol == "AAPL"

    def test_corrupt_file_returns_default(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text("not json")
        data = load_watchlists(path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"

    def test_non_dict_returns_default(self, tmp_path):
        path = tmp_path / "watchlists.json"
        path.write_text(json.dumps(["not", "a", "dict"]))
        data = load_watchlists(path)
        assert len(data.watchlists) == 1


class TestSaveWatchlists:
    def test_round_trip(self, tmp_path):
        path = tmp_path / "watchlists.json"
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Tech",
                    items=[
                        WatchlistItem(type="equity", symbol="AAPL"),
                        WatchlistItem(
                            type="option",
                            symbol="AAPL",
                            strike=180.0,
                            option_type="put",
                            expiration="2026-04-17",
                        ),
                    ],
                )
            ],
            active_index=0,
        )
        save_watchlists(data, path)
        loaded = load_watchlists(path)
        assert len(loaded.watchlists) == 1
        assert loaded.watchlists[0].name == "Tech"
        assert len(loaded.watchlists[0].items) == 2
        assert loaded.watchlists[0].items[1].strike == 180.0

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "watchlists.json"
        data = WatchlistData(
            watchlists=[Watchlist(name="Default", items=[])], active_index=0
        )
        save_watchlists(data, path)
        assert path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlists.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenortui.watchlists'`

- [ ] **Step 3: Implement data models and load/save**

```python
# src/tenortui/watchlists.py
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

DEFAULT_WATCHLISTS_PATH = Path.home() / ".config" / "tenor" / "watchlists.json"


@dataclass
class WatchlistItem:
    type: str  # "equity" or "option"
    symbol: str
    strike: float | None = None
    option_type: str | None = None  # "call" or "put"
    expiration: str | None = None  # "2026-04-17"


@dataclass
class Watchlist:
    name: str
    items: list[WatchlistItem] = field(default_factory=list)


@dataclass
class WatchlistData:
    watchlists: list[Watchlist] = field(default_factory=list)
    active_index: int = 0


def _default_data() -> WatchlistData:
    return WatchlistData(watchlists=[Watchlist(name="Default")])


def load_watchlists(path: Path = DEFAULT_WATCHLISTS_PATH) -> WatchlistData:
    if not path.exists():
        return _default_data()
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return _default_data()
    if not isinstance(raw, dict):
        return _default_data()
    watchlists = []
    for wl in raw.get("watchlists", []):
        items = [WatchlistItem(**item) for item in wl.get("items", [])]
        watchlists.append(Watchlist(name=wl.get("name", "Unnamed"), items=items))
    if not watchlists:
        return _default_data()
    return WatchlistData(
        watchlists=watchlists,
        active_index=raw.get("active_index", 0),
    )


def save_watchlists(data: WatchlistData, path: Path = DEFAULT_WATCHLISTS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {
        "watchlists": [
            {
                "name": wl.name,
                "items": [
                    {k: v for k, v in asdict(item).items() if v is not None}
                    for item in wl.items
                ],
            }
            for wl in data.watchlists
        ],
        "active_index": data.active_index,
    }
    path.write_text(json.dumps(raw, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlists.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/watchlists.py tests/test_watchlists.py
git commit -m "feat: add watchlist data models and persistence

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Watchlist CRUD Operations

**Files:**
- Modify: `src/tenortui/watchlists.py`
- Modify: `tests/test_watchlists.py`

- [ ] **Step 1: Write failing tests for CRUD operations**

Append to `tests/test_watchlists.py`:

```python
from tenortui.watchlists import (
    add_item,
    remove_item,
    create_watchlist,
    rename_watchlist,
    delete_watchlist,
)


class TestAddItem:
    def test_add_equity(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        item = WatchlistItem(type="equity", symbol="AAPL")
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].symbol == "AAPL"

    def test_add_option(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        item = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].strike == 180.0

    def test_deduplicates_equity(self):
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default",
                    items=[WatchlistItem(type="equity", symbol="AAPL")],
                )
            ]
        )
        item = WatchlistItem(type="equity", symbol="AAPL")
        result = add_item(data, 0, item)
        assert len(result.watchlists[0].items) == 1

    def test_deduplicates_option(self):
        existing = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        data = WatchlistData(
            watchlists=[Watchlist(name="Default", items=[existing])]
        )
        result = add_item(data, 0, existing)
        assert len(result.watchlists[0].items) == 1

    def test_does_not_deduplicate_different_options(self):
        existing = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=180.0,
            option_type="put",
            expiration="2026-04-17",
        )
        new = WatchlistItem(
            type="option",
            symbol="AAPL",
            strike=200.0,
            option_type="call",
            expiration="2026-04-17",
        )
        data = WatchlistData(
            watchlists=[Watchlist(name="Default", items=[existing])]
        )
        result = add_item(data, 0, new)
        assert len(result.watchlists[0].items) == 2


class TestRemoveItem:
    def test_removes_by_index(self):
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default",
                    items=[
                        WatchlistItem(type="equity", symbol="AAPL"),
                        WatchlistItem(type="equity", symbol="MSFT"),
                    ],
                )
            ]
        )
        result = remove_item(data, 0, 0)
        assert len(result.watchlists[0].items) == 1
        assert result.watchlists[0].items[0].symbol == "MSFT"

    def test_invalid_index_returns_unchanged(self):
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default",
                    items=[WatchlistItem(type="equity", symbol="AAPL")],
                )
            ]
        )
        result = remove_item(data, 0, 5)
        assert len(result.watchlists[0].items) == 1


class TestCreateWatchlist:
    def test_creates_new(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = create_watchlist(data, "Tech")
        assert len(result.watchlists) == 2
        assert result.watchlists[1].name == "Tech"
        assert result.watchlists[1].items == []


class TestRenameWatchlist:
    def test_renames(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = rename_watchlist(data, 0, "My List")
        assert result.watchlists[0].name == "My List"


class TestDeleteWatchlist:
    def test_deletes(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="Default"), Watchlist(name="Tech")]
        )
        result = delete_watchlist(data, 1)
        assert len(result.watchlists) == 1
        assert result.watchlists[0].name == "Default"

    def test_cannot_delete_last(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        result = delete_watchlist(data, 0)
        assert len(result.watchlists) == 1

    def test_adjusts_active_index(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="A"), Watchlist(name="B")],
            active_index=1,
        )
        result = delete_watchlist(data, 1)
        assert result.active_index == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlists.py::TestAddItem -v`
Expected: FAIL — `ImportError: cannot import name 'add_item'`

- [ ] **Step 3: Implement CRUD operations**

Append to `src/tenortui/watchlists.py`:

```python
def _items_match(a: WatchlistItem, b: WatchlistItem) -> bool:
    if a.type != b.type or a.symbol != b.symbol:
        return False
    if a.type == "equity":
        return True
    return (
        a.strike == b.strike
        and a.option_type == b.option_type
        and a.expiration == b.expiration
    )


def add_item(data: WatchlistData, watchlist_index: int, item: WatchlistItem) -> WatchlistData:
    wl = data.watchlists[watchlist_index]
    if any(_items_match(existing, item) for existing in wl.items):
        return data
    wl.items.append(item)
    return data


def remove_item(data: WatchlistData, watchlist_index: int, item_index: int) -> WatchlistData:
    wl = data.watchlists[watchlist_index]
    if 0 <= item_index < len(wl.items):
        wl.items.pop(item_index)
    return data


def create_watchlist(data: WatchlistData, name: str) -> WatchlistData:
    data.watchlists.append(Watchlist(name=name))
    return data


def rename_watchlist(data: WatchlistData, index: int, name: str) -> WatchlistData:
    data.watchlists[index].name = name
    return data


def delete_watchlist(data: WatchlistData, index: int) -> WatchlistData:
    if len(data.watchlists) <= 1:
        return data
    data.watchlists.pop(index)
    if data.active_index >= len(data.watchlists):
        data.active_index = len(data.watchlists) - 1
    return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlists.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/watchlists.py tests/test_watchlists.py
git commit -m "feat: add watchlist CRUD operations

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: History Migration

**Files:**
- Modify: `src/tenortui/watchlists.py`
- Modify: `tests/test_watchlists.py`

- [ ] **Step 1: Write failing tests for migration**

Append to `tests/test_watchlists.py`:

```python
from tenortui.watchlists import migrate_from_history


class TestMigrateFromHistory:
    def test_migrates_history(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL", "MSFT", "GOOG"]))

        data = migrate_from_history(history_path, watchlists_path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].name == "Default"
        assert len(data.watchlists[0].items) == 3
        assert data.watchlists[0].items[0].symbol == "AAPL"
        assert data.watchlists[0].items[0].type == "equity"
        assert data.watchlists[0].items[2].symbol == "GOOG"
        # Should have saved to watchlists.json
        assert watchlists_path.exists()

    def test_no_history_returns_default(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        data = migrate_from_history(history_path, watchlists_path)
        assert len(data.watchlists) == 1
        assert data.watchlists[0].items == []

    def test_skips_if_watchlists_exist(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL"]))
        watchlists_path.write_text(
            json.dumps(
                {
                    "watchlists": [
                        {"name": "Existing", "items": [{"type": "equity", "symbol": "MSFT"}]}
                    ],
                    "active_index": 0,
                }
            )
        )
        data = migrate_from_history(history_path, watchlists_path)
        assert data.watchlists[0].name == "Existing"
        assert len(data.watchlists[0].items) == 1
        assert data.watchlists[0].items[0].symbol == "MSFT"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlists.py::TestMigrateFromHistory -v`
Expected: FAIL — `ImportError: cannot import name 'migrate_from_history'`

- [ ] **Step 3: Implement migration**

Add to `src/tenortui/watchlists.py` (after the existing imports, add `from tenortui.history import load_history, DEFAULT_HISTORY_PATH`):

```python
def migrate_from_history(
    history_path: Path = DEFAULT_HISTORY_PATH,
    watchlists_path: Path = DEFAULT_WATCHLISTS_PATH,
) -> WatchlistData:
    if watchlists_path.exists():
        return load_watchlists(watchlists_path)
    symbols = load_history(history_path)
    items = [WatchlistItem(type="equity", symbol=s) for s in symbols]
    data = WatchlistData(watchlists=[Watchlist(name="Default", items=items)])
    if symbols:
        save_watchlists(data, watchlists_path)
    return data
```

Add import at top of `src/tenortui/watchlists.py`:
```python
from tenortui.history import load_history, DEFAULT_HISTORY_PATH
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlists.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/watchlists.py tests/test_watchlists.py
git commit -m "feat: add history-to-watchlist migration

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: WatchlistPanel Widget

**Files:**
- Create: `src/tenortui/widgets/watchlist_panel.py`
- Create: `tests/test_watchlist_panel.py`

- [ ] **Step 1: Write failing tests for the widget**

```python
# tests/test_watchlist_panel.py
import pytest
from datetime import date, timedelta

from tenortui.models import Quote, OptionContract
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_panel import WatchlistPanel


@pytest.fixture
def sample_watchlist_data():
    return WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[
                    WatchlistItem(type="equity", symbol="AAPL"),
                    WatchlistItem(
                        type="option",
                        symbol="AAPL",
                        strike=180.0,
                        option_type="put",
                        expiration="2026-04-17",
                    ),
                    WatchlistItem(type="equity", symbol="MSFT"),
                ],
            ),
            Watchlist(name="Tech", items=[]),
        ],
        active_index=0,
    )


@pytest.fixture
def sample_equity_quotes():
    return [
        Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=213.25,
            change=1.42,
            change_percent=0.67,
            volume=54_200_000,
        ),
        Quote(
            symbol="MSFT",
            name="Microsoft Corp.",
            price=415.10,
            change=-2.30,
            change_percent=-0.55,
            volume=32_100_000,
        ),
    ]


class TestWatchlistPanelGrouping:
    def test_groups_by_underlying(self, sample_watchlist_data):
        panel = WatchlistPanel()
        groups = panel._build_display_groups(sample_watchlist_data.watchlists[0].items)
        # AAPL group: 1 equity + 1 option, MSFT group: 1 equity
        assert len(groups) == 2
        assert groups[0][0] == "AAPL"
        assert len(groups[0][1]) == 2  # equity + option
        assert groups[1][0] == "MSFT"
        assert len(groups[1][1]) == 1  # equity only

    def test_option_only_group(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(
                type="option",
                symbol="GOOG",
                strike=150.0,
                option_type="call",
                expiration="2026-04-17",
            )
        ]
        groups = panel._build_display_groups(items)
        assert len(groups) == 1
        assert groups[0][0] == "GOOG"


class TestWatchlistPanelDTE:
    def test_dte_calculation(self):
        panel = WatchlistPanel()
        future = (date.today() + timedelta(days=30)).isoformat()
        assert panel._calculate_dte(future) == 30

    def test_dte_warning_threshold(self):
        panel = WatchlistPanel()
        near_expiry = (date.today() + timedelta(days=5)).isoformat()
        assert panel._calculate_dte(near_expiry) <= 7


class TestWatchlistPanelRemove:
    def test_remove_returns_item(self, sample_watchlist_data):
        panel = WatchlistPanel()
        panel._watchlist_data = sample_watchlist_data
        panel._active_index = 0
        # Simulate selected flat index 0 -> first item (AAPL equity)
        removed = panel._get_item_at_flat_index(0)
        assert removed is not None
        assert removed.symbol == "AAPL"
        assert removed.type == "equity"

    def test_flat_index_maps_to_option(self, sample_watchlist_data):
        panel = WatchlistPanel()
        panel._watchlist_data = sample_watchlist_data
        panel._active_index = 0
        # Flat index 1 -> AAPL option
        item = panel._get_item_at_flat_index(1)
        assert item is not None
        assert item.type == "option"
        assert item.strike == 180.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlist_panel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenortui.widgets.watchlist_panel'`

- [ ] **Step 3: Implement WatchlistPanel widget**

```python
# src/tenortui/widgets/watchlist_panel.py
from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Static

from tenortui.models import OptionContract, Quote
from tenortui.watchlists import WatchlistData, WatchlistItem


class WatchlistPanel(Widget):
    DEFAULT_CSS = """
    WatchlistPanel {
        height: 1fr;
    }
    WatchlistPanel .wl-tab-bar {
        height: 1;
        padding: 0 1;
    }
    WatchlistPanel .wl-tab {
        min-width: 8;
        height: 1;
        margin: 0 1 0 0;
        background: $surface;
        color: $text-muted;
    }
    WatchlistPanel .wl-tab.active {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    WatchlistPanel ListView {
        height: auto;
        max-height: 100%;
        padding: 0 1;
    }
    WatchlistPanel ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistPanel .wl-empty {
        padding: 1;
        color: $text-muted;
        content-align: center middle;
        height: 1fr;
    }
    WatchlistPanel .wl-loading {
        padding: 0 1;
        color: $text-muted;
    }
    WatchlistPanel .wl-contract {
        color: $text-muted;
    }
    WatchlistPanel .wl-contract-warning {
        color: yellow;
    }
    """

    class TickerSelected(Message):
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol
            super().__init__()

    class WatchlistChanged(Message):
        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    def __init__(self) -> None:
        super().__init__()
        self._watchlist_data: WatchlistData | None = None
        self._active_index: int = 0
        self._equity_quotes: dict[str, Quote] = {}
        self._contract_quotes: dict[tuple[str, str], list[OptionContract]] = {}
        self._flat_items: list[WatchlistItem] = []

    def compose(self) -> ComposeResult:
        yield Horizontal(classes="wl-tab-bar")
        yield Static("Loading...", classes="wl-loading", id="wl-loading")
        yield ListView()
        yield Static(
            "Press w to add a ticker to your watchlist", classes="wl-empty", id="wl-empty"
        )

    def set_watchlists(self, data: WatchlistData) -> None:
        self._watchlist_data = data
        self._active_index = data.active_index
        self._rebuild_tabs()
        self._rebuild_list()

    def _rebuild_tabs(self) -> None:
        if self._watchlist_data is None:
            return
        tab_bar = self.query_one(".wl-tab-bar", Horizontal)
        tab_bar.remove_children()
        for i, wl in enumerate(self._watchlist_data.watchlists):
            classes = "wl-tab active" if i == self._active_index else "wl-tab"
            btn = Button(wl.name, classes=classes, id=f"wl-tab-{i}")
            tab_bar.mount(btn)

    def _rebuild_list(self) -> None:
        if self._watchlist_data is None:
            return
        wl = self._watchlist_data.watchlists[self._active_index]
        list_view = self.query_one(ListView)
        list_view.clear()
        loading = self.query_one("#wl-loading", Static)
        empty = self.query_one("#wl-empty", Static)

        if not wl.items:
            loading.display = False
            empty.display = True
            list_view.display = False
            return

        empty.display = False
        list_view.display = True

        self._flat_items = []
        groups = self._build_display_groups(wl.items)

        for symbol, items in groups:
            for item in items:
                self._flat_items.append(item)
                if item.type == "equity":
                    quote = self._equity_quotes.get(symbol)
                    if quote:
                        change_sign = "+" if quote.change >= 0 else ""
                        text = (
                            f"{quote.symbol:<6} "
                            f"${quote.price:>10.2f}  "
                            f"{change_sign}{quote.change:.2f} "
                            f"({change_sign}{quote.change_percent:.2f}%)"
                        )
                    else:
                        text = f"{symbol}"
                    list_view.append(ListItem(Label(text)))
                else:
                    dte = self._calculate_dte(item.expiration) if item.expiration else 0
                    contract = self._find_contract_quote(item)
                    dte_str = f"DTE: {dte}"
                    warning = dte <= 7
                    if contract:
                        text = (
                            f"  {item.strike:.0f}"
                            f"{'P' if item.option_type == 'put' else 'C'} "
                            f"{item.expiration[5:] if item.expiration else ''}  "
                            f"{contract.bid:.2f}/{contract.ask:.2f}  "
                            f"mid {contract.mid:.2f}  "
                            f"{dte_str}"
                        )
                    else:
                        type_char = "P" if item.option_type == "put" else "C"
                        text = (
                            f"  {item.strike:.0f}{type_char} "
                            f"{item.expiration[5:] if item.expiration else ''}  "
                            f"{dte_str}"
                        )
                    cls = "wl-contract-warning" if warning else "wl-contract"
                    list_view.append(ListItem(Label(text, classes=cls)))

        loading.display = False
        if self._flat_items:
            list_view.index = 0

    def _build_display_groups(
        self, items: list[WatchlistItem]
    ) -> list[tuple[str, list[WatchlistItem]]]:
        groups: dict[str, list[WatchlistItem]] = {}
        order: list[str] = []
        for item in items:
            if item.symbol not in groups:
                groups[item.symbol] = []
                order.append(item.symbol)
            groups[item.symbol].append(item)
        return [(symbol, groups[symbol]) for symbol in order]

    def _calculate_dte(self, expiration: str) -> int:
        exp_date = date.fromisoformat(expiration)
        return (exp_date - date.today()).days

    def _find_contract_quote(self, item: WatchlistItem) -> OptionContract | None:
        if item.expiration is None:
            return None
        contracts = self._contract_quotes.get((item.symbol, item.expiration), [])
        for c in contracts:
            if (
                c.strike == item.strike
                and c.option_type == item.option_type
            ):
                return c
        return None

    def _get_item_at_flat_index(self, index: int) -> WatchlistItem | None:
        if 0 <= index < len(self._flat_items):
            return self._flat_items[index]
        return None

    def get_selected_item(self) -> WatchlistItem | None:
        list_view = self.query_one(ListView)
        if list_view.index is not None:
            return self._get_item_at_flat_index(list_view.index)
        return None

    def update_equity_quotes(self, quotes: list[Quote]) -> None:
        for q in quotes:
            self._equity_quotes[q.symbol] = q
        self._rebuild_list()

    def update_contract_quotes(
        self, contracts: dict[tuple[str, str], list[OptionContract]]
    ) -> None:
        self._contract_quotes.update(contracts)
        self._rebuild_list()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("wl-tab-"):
            index = int(btn_id.split("-")[-1])
            self._active_index = index
            if self._watchlist_data:
                self._watchlist_data.active_index = index
            self._rebuild_tabs()
            self._rebuild_list()
            self.post_message(self.WatchlistChanged(index))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = self.get_selected_item()
        if item and item.type == "equity":
            self.post_message(self.TickerSelected(item.symbol))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlist_panel.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/watchlist_panel.py tests/test_watchlist_panel.py
git commit -m "feat: add WatchlistPanel widget with grouped display

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: WatchlistPicker Modal

**Files:**
- Create: `src/tenortui/widgets/watchlist_picker.py`
- Create: `tests/test_watchlist_picker.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_watchlist_picker.py
import pytest

from tenortui.watchlists import WatchlistData, Watchlist
from tenortui.widgets.watchlist_picker import WatchlistPicker, WatchlistManager


class TestWatchlistPickerInit:
    def test_stores_watchlist_names(self):
        data = WatchlistData(
            watchlists=[Watchlist(name="Default"), Watchlist(name="Tech")]
        )
        picker = WatchlistPicker(data)
        assert picker._watchlist_data is data
        assert len(data.watchlists) == 2


class TestWatchlistManagerInit:
    def test_stores_data(self):
        data = WatchlistData(watchlists=[Watchlist(name="Default")])
        manager = WatchlistManager(data)
        assert manager._watchlist_data is data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlist_picker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement WatchlistPicker and WatchlistManager**

```python
# src/tenortui/widgets/watchlist_picker.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from tenortui.watchlists import (
    WatchlistData,
    create_watchlist,
    delete_watchlist,
    rename_watchlist,
)


class WatchlistPicker(ModalScreen[int | None]):
    """Modal to pick which watchlist to add an item to."""

    DEFAULT_CSS = """
    WatchlistPicker {
        align: center middle;
    }
    WatchlistPicker #picker-container {
        width: 40;
        max-height: 60%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    WatchlistPicker .picker-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    WatchlistPicker ListView {
        height: auto;
        max-height: 100%;
    }
    WatchlistPicker ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistPicker .picker-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    WatchlistPicker #picker-new-input {
        display: none;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("n", "new_watchlist", "New", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, data: WatchlistData) -> None:
        super().__init__()
        self._watchlist_data = data
        self._creating_new = False

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-container"):
            yield Static("Add to Watchlist", classes="picker-title")
            lv = ListView()
            for wl in self._watchlist_data.watchlists:
                lv.append(ListItem(Label(wl.name)))
            yield lv
            yield Input(placeholder="New watchlist name", id="picker-new-input")
            yield Static("[n] New  [Esc] Cancel", classes="picker-footer")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._creating_new:
            index = self.query_one(ListView).index
            self.dismiss(index)

    def action_cancel(self) -> None:
        if self._creating_new:
            self._creating_new = False
            self.query_one("#picker-new-input", Input).display = False
            self.query_one(ListView).focus()
        else:
            self.dismiss(None)

    def action_new_watchlist(self) -> None:
        if self._creating_new:
            return
        self._creating_new = True
        inp = self.query_one("#picker-new-input", Input)
        inp.display = True
        inp.value = ""
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name:
            create_watchlist(self._watchlist_data, name)
            new_index = len(self._watchlist_data.watchlists) - 1
            self.dismiss(new_index)

    def action_cursor_down(self) -> None:
        if not self._creating_new:
            self.query_one(ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if not self._creating_new:
            self.query_one(ListView).action_cursor_up()


class WatchlistManager(ModalScreen[WatchlistData | None]):
    """Modal to manage watchlists (create, rename, delete)."""

    DEFAULT_CSS = """
    WatchlistManager {
        align: center middle;
    }
    WatchlistManager #manager-container {
        width: 45;
        max-height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    WatchlistManager .manager-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    WatchlistManager ListView {
        height: auto;
        max-height: 100%;
    }
    WatchlistManager ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistManager .manager-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    WatchlistManager #manager-input {
        display: none;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("n", "new_watchlist", "New", show=False),
        Binding("r", "rename_watchlist", "Rename", show=False),
        Binding("d", "delete_watchlist", "Delete", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, data: WatchlistData) -> None:
        super().__init__()
        self._watchlist_data = data
        self._editing: str | None = None  # "new" or "rename"

    def compose(self) -> ComposeResult:
        with Vertical(id="manager-container"):
            yield Static("Manage Watchlists", classes="manager-title")
            yield ListView()
            yield Input(placeholder="Watchlist name", id="manager-input")
            yield Static(
                "[n] New  [r] Rename  [d] Delete  [Esc] Close",
                classes="manager-footer",
            )
        self._rebuild_list()

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        lv = self.query_one(ListView)
        lv.clear()
        for wl in self._watchlist_data.watchlists:
            count = len(wl.items)
            label = f"{wl.name} ({count} item{'s' if count != 1 else ''})"
            lv.append(ListItem(Label(label)))

    def action_close(self) -> None:
        if self._editing:
            self._editing = None
            self.query_one("#manager-input", Input).display = False
            self.query_one(ListView).focus()
        else:
            self.dismiss(self._watchlist_data)

    def action_new_watchlist(self) -> None:
        if self._editing:
            return
        self._editing = "new"
        inp = self.query_one("#manager-input", Input)
        inp.display = True
        inp.value = ""
        inp.placeholder = "New watchlist name"
        inp.focus()

    def action_rename_watchlist(self) -> None:
        if self._editing:
            return
        lv = self.query_one(ListView)
        if lv.index is None:
            return
        self._editing = "rename"
        inp = self.query_one("#manager-input", Input)
        inp.display = True
        inp.value = self._watchlist_data.watchlists[lv.index].name
        inp.placeholder = "New name"
        inp.focus()

    def action_delete_watchlist(self) -> None:
        if self._editing:
            return
        lv = self.query_one(ListView)
        if lv.index is None:
            return
        if len(self._watchlist_data.watchlists) <= 1:
            return
        delete_watchlist(self._watchlist_data, lv.index)
        self._rebuild_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            return
        if self._editing == "new":
            create_watchlist(self._watchlist_data, name)
        elif self._editing == "rename":
            lv = self.query_one(ListView)
            if lv.index is not None:
                rename_watchlist(self._watchlist_data, lv.index, name)
        self._editing = None
        self.query_one("#manager-input", Input).display = False
        self._rebuild_list()
        self.query_one(ListView).focus()

    def action_cursor_down(self) -> None:
        if not self._editing:
            self.query_one(ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if not self._editing:
            self.query_one(ListView).action_cursor_up()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlist_picker.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/tenortui/widgets/watchlist_picker.py tests/test_watchlist_picker.py
git commit -m "feat: add WatchlistPicker and WatchlistManager modals

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Integrate WatchlistPanel into App (Replace RecentlyViewed)

**Files:**
- Modify: `src/tenortui/app.py`
- Modify: `src/tenortui/widgets/help_overlay.py`

- [ ] **Step 1: Update imports in app.py**

Replace the history and RecentlyViewed imports in `src/tenortui/app.py`:

Replace lines 19 and 29:
```python
# OLD
from tenortui.history import load_history, add_to_history
...
from tenortui.widgets.recently_viewed import RecentlyViewed
```

With:
```python
from tenortui.watchlists import (
    WatchlistData,
    WatchlistItem,
    add_item,
    load_watchlists,
    migrate_from_history,
    remove_item,
    save_watchlists,
)
from tenortui.widgets.watchlist_panel import WatchlistPanel
from tenortui.widgets.watchlist_picker import WatchlistPicker, WatchlistManager
```

- [ ] **Step 2: Update __init__ to use watchlists**

In `src/tenortui/app.py`, replace `self._history = load_history()` (line 67) with:
```python
self._watchlist_data = migrate_from_history()
```

- [ ] **Step 3: Update compose() to yield WatchlistPanel**

Replace `yield RecentlyViewed(symbols=self._history)` (line 91) with:
```python
yield WatchlistPanel()
```

- [ ] **Step 4: Update on_mount() to use watchlists**

Replace the on_mount method (lines 96-109):
```python
def on_mount(self) -> None:
    chain_table = self.query_one(ChainTable)
    watchlist_panel = self.query_one(WatchlistPanel)
    watchlist_panel.set_watchlists(self._watchlist_data)
    has_items = bool(
        self._watchlist_data.watchlists
        and any(wl.items for wl in self._watchlist_data.watchlists)
    )
    if has_items:
        chain_table.display = False
        self._fetch_watchlist_quotes()
    else:
        watchlist_panel.display = False
    self._update_market_display()
    self.query_one(StatusBar).update_rate_display(
        self._risk_free_rate, self._risk_free_rate_is_live
    )
    self.set_interval(60, self._update_market_display)
```

- [ ] **Step 5: Replace _fetch_recent_quotes with _fetch_watchlist_quotes**

Replace the `_fetch_recent_quotes` method (lines 317-327) with:
```python
@work(exclusive=True, group="watchlist-quotes")
async def _fetch_watchlist_quotes(self) -> None:
    wl = self._watchlist_data.watchlists[self._watchlist_data.active_index]
    panel = self.query_one(WatchlistPanel)

    # Fetch equity quotes
    equity_symbols = list({item.symbol for item in wl.items if item.type == "equity"})
    if equity_symbols:
        quotes = await asyncio.to_thread(batch_quotes, equity_symbols)
        panel.update_equity_quotes(quotes)

    # Fetch contract quotes grouped by (symbol, expiration)
    contract_groups: dict[tuple[str, str], list[WatchlistItem]] = {}
    for item in wl.items:
        if item.type == "option" and item.expiration:
            key = (item.symbol, item.expiration)
            contract_groups.setdefault(key, []).append(item)

    if contract_groups:
        from tenortui.models import OptionContract

        all_contracts: dict[tuple[str, str], list[OptionContract]] = {}
        for (symbol, expiration) in contract_groups:
            try:
                chain = await asyncio.to_thread(
                    self._provider.get_chain, symbol, expiration
                )
                all_contracts[(symbol, expiration)] = chain.calls + chain.puts
            except Exception:
                continue
        panel.update_contract_quotes(all_contracts)

    # Focus the ListView
    from textual.widgets import ListView

    try:
        panel.query_one(ListView).focus()
    except Exception:
        pass
```

- [ ] **Step 6: Update _load_ticker to add to watchlist instead of history**

In `_load_ticker` (line 350), replace:
```python
self._history = add_to_history(symbol)
```
With:
```python
item = WatchlistItem(type="equity", symbol=symbol)
add_item(self._watchlist_data, self._watchlist_data.active_index, item)
save_watchlists(self._watchlist_data)
self.query_one(WatchlistPanel).set_watchlists(self._watchlist_data)
```

- [ ] **Step 7: Update _load_ticker to hide WatchlistPanel instead of RecentlyViewed**

In `_load_ticker` (lines 339-341), replace:
```python
recently_viewed = self.query_one(RecentlyViewed)
recently_viewed.display = False
chain_table.display = True
```
With:
```python
self.query_one(WatchlistPanel).display = False
chain_table.display = True
```

- [ ] **Step 8: Add watchlist message handlers**

Add after the existing `on_expiry_selector_expiry_selected` method:
```python
def on_watchlist_panel_ticker_selected(
    self, event: WatchlistPanel.TickerSelected
) -> None:
    self._current_symbol = event.symbol
    self._load_ticker(event.symbol)

def on_watchlist_panel_watchlist_changed(
    self, event: WatchlistPanel.WatchlistChanged
) -> None:
    self._watchlist_data.active_index = event.index
    save_watchlists(self._watchlist_data)
    self._fetch_watchlist_quotes()
```

- [ ] **Step 9: Extend auto-refresh to include watchlist quotes**

In `_on_auto_refresh` (lines 207-216), add watchlist refresh. Replace:
```python
def _on_auto_refresh(self) -> None:
    """Fired when the auto-refresh timer expires."""
    if self._current_symbol and self._auto_refresh_enabled:
        if self._current_expiration:
            self._load_chain(self._current_symbol, self._current_expiration)
        else:
            self._load_ticker(self._current_symbol)
    if self._auto_refresh_enabled:
        self._start_auto_refresh()
```
With:
```python
def _on_auto_refresh(self) -> None:
    """Fired when the auto-refresh timer expires."""
    if self._current_symbol and self._auto_refresh_enabled:
        if self._current_expiration:
            self._load_chain(self._current_symbol, self._current_expiration)
        else:
            self._load_ticker(self._current_symbol)
    if self._auto_refresh_enabled:
        self._fetch_watchlist_quotes()
        self._start_auto_refresh()
```

- [ ] **Step 10: Update help overlay keybindings**

In `src/tenortui/widgets/help_overlay.py`, add watchlist keybindings to the KEYBINDINGS list. Add a new section after the "Panels" section (after line 36):

```python
(
    "Watchlists",
    [
        ("w", "Add ticker/contract to watchlist"),
        ("W", "Open watchlist manager"),
        ("d", "Remove item from watchlist"),
    ],
),
```

- [ ] **Step 11: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All existing tests pass. Some may need updates if they reference `RecentlyViewed` directly.

- [ ] **Step 12: Fix any broken tests**

If any tests reference `RecentlyViewed`, update them to use `WatchlistPanel` instead. Check for:
- `self.query_one(RecentlyViewed)` in test files
- Imports of `RecentlyViewed`

- [ ] **Step 13: Commit**

```bash
git add src/tenortui/app.py src/tenortui/widgets/help_overlay.py
git commit -m "feat: integrate WatchlistPanel into app, replace RecentlyViewed

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Add Keybindings for Watchlist Actions

**Files:**
- Modify: `src/tenortui/app.py`

- [ ] **Step 1: Add `w` keybinding handler in on_key()**

In `src/tenortui/app.py`, in the `on_key` method, add handling for `w`, `W`, and `d` keys. Add after the `elif key == "r":` block (before the end of `on_key`):

```python
elif key == "w":
    self._action_add_to_watchlist()
    event.prevent_default()
elif key == "W":
    self._action_open_watchlist_manager()
    event.prevent_default()
elif key == "d":
    self._action_remove_from_watchlist()
    event.prevent_default()
```

- [ ] **Step 2: Implement _action_add_to_watchlist()**

Add to `src/tenortui/app.py`:

```python
def _action_add_to_watchlist(self) -> None:
    from textual.widgets import DataTable

    item: WatchlistItem | None = None

    # If focused on a DataTable (chain table), add the highlighted contract
    if isinstance(self.focused, DataTable):
        chain_table = self.query_one(ChainTable)
        item = self._get_contract_from_chain_table()
    elif self._current_symbol:
        item = WatchlistItem(type="equity", symbol=self._current_symbol)

    if item is None:
        return

    self._pending_watchlist_item = item
    self.push_screen(
        WatchlistPicker(self._watchlist_data),
        callback=self._on_watchlist_picked,
    )

def _get_contract_from_chain_table(self) -> WatchlistItem | None:
    from textual.widgets import DataTable

    if not isinstance(self.focused, DataTable):
        return None
    table = self.focused
    if table.cursor_row is None or table.row_count == 0:
        return None

    row_idx = table.cursor_row
    row_data = table.get_row_at(row_idx)
    # Skip ATM marker rows
    if row_data and str(row_data[0]).startswith("──"):
        return None

    try:
        strike = float(str(row_data[0]))
    except (ValueError, IndexError):
        return None

    # Determine if this is a call or put table by checking parent labels
    chain_table = self.query_one(ChainTable)
    tables = chain_table.query(DataTable)
    table_list = list(tables)
    if len(table_list) >= 2:
        option_type = "call" if table is table_list[0] else "put"
    else:
        option_type = "call"

    if self._current_symbol and self._current_expiration:
        return WatchlistItem(
            type="option",
            symbol=self._current_symbol,
            strike=strike,
            option_type=option_type,
            expiration=self._current_expiration,
        )
    return None

def _on_watchlist_picked(self, result: int | None) -> None:
    if result is None or not hasattr(self, "_pending_watchlist_item"):
        return
    item = self._pending_watchlist_item
    del self._pending_watchlist_item
    add_item(self._watchlist_data, result, item)
    save_watchlists(self._watchlist_data)
    self.query_one(WatchlistPanel).set_watchlists(self._watchlist_data)
```

- [ ] **Step 3: Implement _action_open_watchlist_manager()**

```python
def _action_open_watchlist_manager(self) -> None:
    self.push_screen(
        WatchlistManager(self._watchlist_data),
        callback=self._on_watchlist_manager_closed,
    )

def _on_watchlist_manager_closed(self, result: WatchlistData | None) -> None:
    if result is not None:
        self._watchlist_data = result
        save_watchlists(self._watchlist_data)
        self.query_one(WatchlistPanel).set_watchlists(self._watchlist_data)
        self._fetch_watchlist_quotes()
```

- [ ] **Step 4: Implement _action_remove_from_watchlist()**

```python
def _action_remove_from_watchlist(self) -> None:
    from textual.widgets import ListView

    panel = self.query_one(WatchlistPanel)
    if not isinstance(self.focused, ListView):
        return
    # Check if the focused ListView belongs to the WatchlistPanel
    if self.focused not in panel.query(ListView):
        return
    lv = self.focused
    if lv.index is None:
        return
    remove_item(self._watchlist_data, self._watchlist_data.active_index, lv.index)
    save_watchlists(self._watchlist_data)
    panel.set_watchlists(self._watchlist_data)
```

- [ ] **Step 5: Run full test suite**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/tenortui/app.py
git commit -m "feat: add w/W/d keybindings for watchlist management

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Integration Tests

**Files:**
- Create: `tests/test_watchlist_integration.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add watchlist fixtures to conftest.py**

Append to `tests/conftest.py`:

```python
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem


@pytest.fixture
def sample_watchlist_data():
    return WatchlistData(
        watchlists=[
            Watchlist(
                name="Default",
                items=[WatchlistItem(type="equity", symbol="AAPL")],
            )
        ],
        active_index=0,
    )
```

- [ ] **Step 2: Write integration tests**

```python
# tests/test_watchlist_integration.py
import json

import pytest

from tenortui.app import TenorTUI
from tenortui.watchlists import (
    WatchlistData,
    Watchlist,
    WatchlistItem,
    load_watchlists,
    save_watchlists,
    migrate_from_history,
)
from tenortui.widgets.watchlist_panel import WatchlistPanel


class TestMigrationIntegration:
    def test_migrates_history_on_first_run(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL", "MSFT"]))

        data = migrate_from_history(history_path, watchlists_path)

        assert watchlists_path.exists()
        assert len(data.watchlists) == 1
        assert len(data.watchlists[0].items) == 2
        assert data.watchlists[0].items[0].symbol == "AAPL"
        assert data.watchlists[0].items[1].symbol == "MSFT"

    def test_does_not_overwrite_existing_watchlists(self, tmp_path):
        history_path = tmp_path / "history.json"
        watchlists_path = tmp_path / "watchlists.json"
        history_path.write_text(json.dumps(["AAPL"]))
        existing = WatchlistData(
            watchlists=[
                Watchlist(
                    name="My List",
                    items=[WatchlistItem(type="equity", symbol="GOOG")],
                )
            ]
        )
        save_watchlists(existing, watchlists_path)

        data = migrate_from_history(history_path, watchlists_path)
        assert data.watchlists[0].name == "My List"
        assert data.watchlists[0].items[0].symbol == "GOOG"


class TestWatchlistPersistence:
    def test_save_and_load_round_trip(self, tmp_path):
        path = tmp_path / "watchlists.json"
        data = WatchlistData(
            watchlists=[
                Watchlist(
                    name="Tech",
                    items=[
                        WatchlistItem(type="equity", symbol="AAPL"),
                        WatchlistItem(
                            type="option",
                            symbol="AAPL",
                            strike=180.0,
                            option_type="put",
                            expiration="2026-04-17",
                        ),
                    ],
                ),
                Watchlist(name="Finance", items=[]),
            ],
            active_index=1,
        )
        save_watchlists(data, path)
        loaded = load_watchlists(path)

        assert len(loaded.watchlists) == 2
        assert loaded.watchlists[0].name == "Tech"
        assert loaded.active_index == 1
        assert loaded.watchlists[0].items[1].strike == 180.0
        assert loaded.watchlists[0].items[1].option_type == "put"


class TestAppWithWatchlists:
    @pytest.mark.asyncio
    async def test_watchlist_panel_mounted(self, fake_provider, monkeypatch):
        monkeypatch.setattr(
            "tenortui.app.migrate_from_history",
            lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
        )
        app = TenorTUI(provider=fake_provider)
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_ticker_added_to_watchlist_on_search(
        self, fake_provider, monkeypatch
    ):
        wl_data = WatchlistData(
            watchlists=[Watchlist(name="Default")], active_index=0
        )
        monkeypatch.setattr(
            "tenortui.app.migrate_from_history", lambda: wl_data
        )
        monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
        monkeypatch.setattr(
            "tenortui.app.batch_quotes", lambda symbols: []
        )
        monkeypatch.setattr(
            "tenortui.app.fetch_fundamentals", lambda q: q
        )
        app = TenorTUI(provider=fake_provider)
        async with app.run_test() as pilot:
            app.action_focus_search()
            await pilot.press(*"AAPL")
            await pilot.press("enter")
            await app.workers.wait_for_complete()

            assert any(
                item.symbol == "AAPL" and item.type == "equity"
                for item in wl_data.watchlists[0].items
            )
```

- [ ] **Step 3: Run integration tests**

Run: `poetry run python -m pytest tests/test_watchlist_integration.py -v`
Expected: All PASS

- [ ] **Step 4: Run full test suite to check nothing is broken**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 5: Fix any broken existing tests**

Look for tests that reference `RecentlyViewed` and update them. Common fixes:
- Replace `from tenortui.widgets.recently_viewed import RecentlyViewed` with `from tenortui.widgets.watchlist_panel import WatchlistPanel`
- Replace `app.query_one(RecentlyViewed)` with `app.query_one(WatchlistPanel)`
- Update monkeypatch targets from `load_history`/`add_to_history` to `migrate_from_history`/`save_watchlists`

- [ ] **Step 6: Commit**

```bash
git add tests/test_watchlist_integration.py tests/conftest.py
git commit -m "test: add watchlist integration tests

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: Sorting Support

**Files:**
- Modify: `src/tenortui/widgets/watchlist_panel.py`
- Modify: `tests/test_watchlist_panel.py`

- [ ] **Step 1: Write failing test for sorting**

Append to `tests/test_watchlist_panel.py`:

```python
class TestWatchlistPanelSorting:
    def test_sort_by_symbol(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="GOOG"),
        ]
        groups = panel._build_display_groups(items, sort_key="symbol")
        assert [g[0] for g in groups] == ["AAPL", "GOOG", "MSFT"]

    def test_sort_by_price(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(symbol="AAPL", name="Apple", price=213.0, change=0, change_percent=0, volume=0),
            "MSFT": Quote(symbol="MSFT", name="Microsoft", price=415.0, change=0, change_percent=0, volume=0),
        }
        items = [
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="MSFT"),
        ]
        groups = panel._build_display_groups(items, sort_key="price")
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]

    def test_sort_by_change(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(symbol="AAPL", name="Apple", price=213.0, change=5.0, change_percent=2.4, volume=0),
            "MSFT": Quote(symbol="MSFT", name="Microsoft", price=415.0, change=-2.0, change_percent=-0.5, volume=0),
        }
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
        ]
        groups = panel._build_display_groups(items, sort_key="change")
        assert [g[0] for g in groups] == ["AAPL", "MSFT"]

    def test_sort_by_volume(self):
        panel = WatchlistPanel()
        panel._equity_quotes = {
            "AAPL": Quote(symbol="AAPL", name="Apple", price=213.0, change=0, change_percent=0, volume=100),
            "MSFT": Quote(symbol="MSFT", name="Microsoft", price=415.0, change=0, change_percent=0, volume=500),
        }
        items = [
            WatchlistItem(type="equity", symbol="AAPL"),
            WatchlistItem(type="equity", symbol="MSFT"),
        ]
        groups = panel._build_display_groups(items, sort_key="volume")
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]

    def test_default_sort_preserves_insertion_order(self):
        panel = WatchlistPanel()
        items = [
            WatchlistItem(type="equity", symbol="MSFT"),
            WatchlistItem(type="equity", symbol="AAPL"),
        ]
        groups = panel._build_display_groups(items)
        assert [g[0] for g in groups] == ["MSFT", "AAPL"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run python -m pytest tests/test_watchlist_panel.py::TestWatchlistPanelSorting -v`
Expected: FAIL — `_build_display_groups() got unexpected keyword argument 'sort_key'`

- [ ] **Step 3: Update _build_display_groups to support sorting**

In `src/tenortui/widgets/watchlist_panel.py`, replace the `_build_display_groups` method:

```python
def _build_display_groups(
    self, items: list[WatchlistItem], sort_key: str | None = None
) -> list[tuple[str, list[WatchlistItem]]]:
    groups: dict[str, list[WatchlistItem]] = {}
    order: list[str] = []
    for item in items:
        if item.symbol not in groups:
            groups[item.symbol] = []
            order.append(item.symbol)
        groups[item.symbol].append(item)

    if sort_key == "symbol":
        order.sort()
    elif sort_key == "price":
        order.sort(
            key=lambda s: self._equity_quotes[s].price
            if s in self._equity_quotes
            else 0,
            reverse=True,
        )
    elif sort_key == "change":
        order.sort(
            key=lambda s: self._equity_quotes[s].change_percent
            if s in self._equity_quotes
            else 0,
            reverse=True,
        )
    elif sort_key == "volume":
        order.sort(
            key=lambda s: self._equity_quotes[s].volume
            if s in self._equity_quotes
            else 0,
            reverse=True,
        )

    return [(symbol, groups[symbol]) for symbol in order]
```

- [ ] **Step 4: Add sort_key state and cycling to WatchlistPanel**

Add to `WatchlistPanel.__init__`:
```python
self._sort_key: str | None = None
```

Add a method to cycle sort:
```python
SORT_KEYS = [None, "symbol", "price", "change", "volume"]

def cycle_sort(self) -> str | None:
    current_idx = self.SORT_KEYS.index(self._sort_key) if self._sort_key in self.SORT_KEYS else 0
    self._sort_key = self.SORT_KEYS[(current_idx + 1) % len(self.SORT_KEYS)]
    self._rebuild_list()
    return self._sort_key
```

Update `_rebuild_list` to pass `sort_key`:
```python
groups = self._build_display_groups(wl.items, sort_key=self._sort_key)
```

- [ ] **Step 5: Add sort keybinding to app.py**

In `src/tenortui/app.py` `on_key()`, add after the `d` key handler:

```python
elif key == "S":
    panel = self.query_one(WatchlistPanel)
    sort_key = panel.cycle_sort()
    sort_label = sort_key or "default"
    self.query_one(StatusBar).update_refresh_status(
        seconds_until=self._auto_refresh_countdown
    )
    event.prevent_default()
```

Update help overlay — add to the "Watchlists" section:
```python
("S", "Cycle sort order (default/symbol/price/change/volume)"),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `poetry run python -m pytest tests/test_watchlist_panel.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/tenortui/widgets/watchlist_panel.py tests/test_watchlist_panel.py src/tenortui/app.py src/tenortui/widgets/help_overlay.py
git commit -m "feat: add watchlist sorting by symbol/price/change/volume

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: Cleanup and Lint

**Files:**
- Modify: various files as needed

- [ ] **Step 1: Run linter**

Run: `poetry run ruff check src/ tests/`
Expected: No errors (or fix any that appear)

- [ ] **Step 2: Run formatter**

Run: `poetry run ruff format --check src/ tests/`
Expected: No changes needed (or run `poetry run ruff format src/ tests/` to fix)

- [ ] **Step 3: Run full test suite one final time**

Run: `poetry run python -m pytest -v`
Expected: All PASS

- [ ] **Step 4: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "chore: lint and format watchlist code

Closes #5

Co-Authored-By: Claude <noreply@anthropic.com>"
```
