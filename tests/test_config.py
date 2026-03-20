import pytest
from pathlib import Path

from tenortui.config import load_config
from tenortui.exceptions import ConfigError


class TestLoadConfig:
    def test_no_config_file_defaults_to_yahoo(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.provider_name == "yahoo"
        assert config.provider_config == {}

    def test_valid_yaml_with_default(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc123\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "tradier"
        assert config.provider_config == {"api_key": "abc123"}

    def test_valid_yaml_no_default_uses_first_provider(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "yahoo"

    def test_no_default_uses_first_provider_key(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ntradier:\n  api_key: abc\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.provider_name == "tradier"

    def test_cli_override(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: yahoo\nyahoo: {}\n")
        config = load_config(config_path=rc, provider_override="tradier")
        assert config.provider_name == "tradier"

    def test_malformed_yaml_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text(":{bad yaml")
        with pytest.raises(ConfigError):
            load_config(config_path=rc)

    def test_unknown_provider_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: nonexistent\n")
        with pytest.raises(ConfigError, match="Unknown provider"):
            load_config(config_path=rc)

    def test_tradier_missing_api_key_raises_config_error(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier: {}\n")
        with pytest.raises(ConfigError, match="api_key"):
            load_config(config_path=rc)

    def test_tradier_sandbox_defaults_false(self, tmp_path):
        rc = tmp_path / ".tenorrc"
        rc.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc\n")
        config = load_config(config_path=rc)
        assert config.provider_config.get("sandbox", False) is False
