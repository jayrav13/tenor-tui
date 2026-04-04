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
