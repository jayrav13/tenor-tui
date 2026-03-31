import yaml

from tenortui.config import save_config, load_config


class TestSaveConfig:
    def test_save_creates_new_file(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        save_config({"default": "tradier"}, config_path=config_path)
        assert config_path.exists()
        data = yaml.safe_load(config_path.read_text())
        assert data["default"] == "tradier"

    def test_save_creates_parent_directories(self, tmp_path):
        config_path = tmp_path / "sub" / "dir" / "config.yaml"
        save_config({"default": "yahoo"}, config_path=config_path)
        assert config_path.exists()

    def test_save_merges_with_existing(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "---\ndefault: yahoo\nspread_thresholds:\n  tight: 5.0\n  moderate: 15.0\n"
        )
        save_config({"spread_thresholds": {"tight": 3.0}}, config_path=config_path)
        data = yaml.safe_load(config_path.read_text())
        assert data["default"] == "yahoo"
        assert data["spread_thresholds"]["tight"] == 3.0
        assert data["spread_thresholds"]["moderate"] == 15.0

    def test_save_deep_merges_nested(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "---\nyahoo:\n  greeks:\n    enabled: false\n    risk_free_rate: 0.05\n"
        )
        save_config({"yahoo": {"greeks": {"enabled": True}}}, config_path=config_path)
        data = yaml.safe_load(config_path.read_text())
        assert data["yahoo"]["greeks"]["enabled"] is True
        assert data["yahoo"]["greeks"]["risk_free_rate"] == 0.05

    def test_save_roundtrip_with_load(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("---\ndefault: yahoo\nrefresh:\n  regular: 60\n")
        save_config({"refresh": {"regular": 30}}, config_path=config_path)
        config = load_config(config_path=config_path)
        assert config.refresh.regular == 30
        assert config.refresh.extended == 120  # default preserved
