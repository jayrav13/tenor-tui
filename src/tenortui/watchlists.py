import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

from tenortui.history import load_history, DEFAULT_HISTORY_PATH

DEFAULT_WATCHLISTS_PATH = Path.home() / ".config" / "tenor" / "watchlists.json"

_KNOWN_ITEM_FIELDS = {"type", "symbol", "strike", "option_type", "expiration"}


@dataclass
class WatchlistItem:
    type: Literal["equity", "option"]
    symbol: str
    strike: float | None = None
    option_type: Literal["call", "put"] | None = None
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


def _parse_item(item: object) -> WatchlistItem | None:
    """Return a WatchlistItem from a raw dict, or None if the item is malformed."""
    if not isinstance(item, dict):
        return None
    if "type" not in item or "symbol" not in item:
        return None
    filtered = {k: v for k, v in item.items() if k in _KNOWN_ITEM_FIELDS}
    try:
        return WatchlistItem(**filtered)
    except TypeError:
        return None


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
        items = [
            parsed
            for item in wl.get("items", [])
            if (parsed := _parse_item(item)) is not None
        ]
        watchlists.append(Watchlist(name=wl.get("name", "Unnamed"), items=items))
    if not watchlists:
        return _default_data()
    raw_index = raw.get("active_index", 0)
    if not isinstance(raw_index, int) or not (0 <= raw_index < len(watchlists)):
        raw_index = 0
    return WatchlistData(
        watchlists=watchlists,
        active_index=raw_index,
    )


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


def add_item(
    data: WatchlistData, watchlist_index: int, item: WatchlistItem
) -> WatchlistData:
    wl = data.watchlists[watchlist_index]
    if any(_items_match(existing, item) for existing in wl.items):
        return data
    wl.items.append(item)
    return data


def remove_item(
    data: WatchlistData, watchlist_index: int, item_index: int
) -> WatchlistData:
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
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(raw, indent=2))
    os.replace(tmp_path, path)
