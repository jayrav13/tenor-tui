import json
from tenortui.history import load_history, save_history, add_to_history

MAX_HISTORY = 10


class TestLoadHistory:
    def test_no_file_returns_empty(self, tmp_path):
        result = load_history(tmp_path / "history.json")
        assert result == []

    def test_valid_file(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["AAPL", "MSFT"]))
        assert load_history(path) == ["AAPL", "MSFT"]

    def test_corrupt_file_returns_empty(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text("not json")
        assert load_history(path) == []

    def test_non_list_returns_empty(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps({"key": "val"}))
        assert load_history(path) == []


class TestSaveHistory:
    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "history.json"
        save_history(["AAPL"], path)
        assert json.loads(path.read_text()) == ["AAPL"]

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["OLD"]))
        save_history(["NEW"], path)
        assert json.loads(path.read_text()) == ["NEW"]


class TestAddToHistory:
    def test_adds_to_front(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["MSFT"]))
        result = add_to_history("AAPL", path)
        assert result == ["AAPL", "MSFT"]

    def test_dedupes_moves_to_front(self, tmp_path):
        path = tmp_path / "history.json"
        path.write_text(json.dumps(["AAPL", "MSFT", "GOOG"]))
        result = add_to_history("MSFT", path)
        assert result == ["MSFT", "AAPL", "GOOG"]

    def test_caps_at_max(self, tmp_path):
        path = tmp_path / "history.json"
        symbols = [f"SYM{i}" for i in range(MAX_HISTORY)]
        path.write_text(json.dumps(symbols))
        result = add_to_history("NEW", path)
        assert len(result) == MAX_HISTORY
        assert result[0] == "NEW"
        assert f"SYM{MAX_HISTORY - 1}" not in result

    def test_empty_history(self, tmp_path):
        path = tmp_path / "history.json"
        result = add_to_history("AAPL", path)
        assert result == ["AAPL"]
