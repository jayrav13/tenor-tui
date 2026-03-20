import json
from pathlib import Path

MAX_HISTORY = 10
DEFAULT_HISTORY_PATH = Path.home() / ".config" / "tenor" / "history.json"


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def save_history(symbols: list[str], path: Path = DEFAULT_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(symbols))


def add_to_history(symbol: str, path: Path = DEFAULT_HISTORY_PATH) -> list[str]:
    symbols = load_history(path)
    if symbol in symbols:
        symbols.remove(symbol)
    symbols.insert(0, symbol)
    symbols = symbols[:MAX_HISTORY]
    save_history(symbols, path)
    return symbols
