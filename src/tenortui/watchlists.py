import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

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
