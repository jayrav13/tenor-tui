import pytest

from tenortui.config import (
    KNOWN_PROVIDERS,
    RefreshConfig,
    SpreadThresholds,
    load_config,
    resolve_config_path,
)
from tenortui.exceptions import ConfigError
from tenortui.providers import PROVIDERS


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

    def test_known_providers_match_registry(self):
        # Regression for #53: argparse reads --provider choices from
        # PROVIDERS, but load_config validated against a hardcoded set,
        # so adding a provider to the registry without updating the set
        # caused `--provider <new>` to be accepted by argparse but
        # rejected at runtime ("Unknown provider"). Single source of
        # truth keeps these in sync.
        assert KNOWN_PROVIDERS == frozenset(PROVIDERS.keys())

    @pytest.mark.parametrize("provider_name", sorted(PROVIDERS.keys()))
    def test_provider_override_accepts_every_registered_provider(
        self, tmp_path, provider_name
    ):
        config = load_config(
            config_path=tmp_path / "nonexistent",
            provider_override=provider_name,
        )
        assert config.provider_name == provider_name

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


class TestConfigPathMigration:
    def test_new_config_path(self, tmp_path):
        config_dir = tmp_path / ".config" / "tenor"
        config_dir.mkdir(parents=True)
        cfg = config_dir / "config.yaml"
        cfg.write_text("---\ndefault: tradier\ntradier:\n  api_key: abc123\n")
        config = load_config(config_path=cfg)
        assert config.provider_name == "tradier"

    def test_fallback_to_tenorrc(self, tmp_path):
        """When new path doesn't exist but ~/.tenorrc does, use it."""
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        old_path = tmp_path / ".tenorrc"
        old_path.write_text("---\ndefault: yahoo\n")
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == old_path

    def test_new_path_takes_precedence(self, tmp_path):
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        new_path.parent.mkdir(parents=True)
        new_path.write_text("---\ndefault: tradier\ntradier:\n  api_key: x\n")
        old_path = tmp_path / ".tenorrc"
        old_path.write_text("---\ndefault: yahoo\n")
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == new_path

    def test_neither_exists_returns_new_path(self, tmp_path):
        new_path = tmp_path / ".config" / "tenor" / "config.yaml"
        old_path = tmp_path / ".tenorrc"
        resolved = resolve_config_path(new_path=new_path, legacy_path=old_path)
        assert resolved == new_path


class TestSpreadThresholds:
    def test_defaults_when_no_config(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.spread_thresholds.tight == 5.0
        assert config.spread_thresholds.moderate == 15.0

    def test_custom_thresholds(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nspread_thresholds:\n  tight: 3.0\n  moderate: 10.0\n"
        )
        config = load_config(config_path=rc)
        assert config.spread_thresholds.tight == 3.0
        assert config.spread_thresholds.moderate == 10.0

    def test_partial_thresholds_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nspread_thresholds:\n  tight: 2.0\n")
        config = load_config(config_path=rc)
        assert config.spread_thresholds.tight == 2.0
        assert config.spread_thresholds.moderate == 15.0

    def test_thresholds_with_provider_override(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nspread_thresholds:\n  tight: 4.0\n  moderate: 12.0\n"
        )
        config = load_config(config_path=rc, provider_override="yahoo")
        assert config.spread_thresholds.tight == 4.0
        assert config.spread_thresholds.moderate == 12.0

    def test_invalid_spread_thresholds_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nspread_thresholds: not_a_dict\n")
        config = load_config(config_path=rc)
        assert config.spread_thresholds == SpreadThresholds()


class TestGreeksConfig:
    def test_defaults_when_no_config(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.greeks.enabled is False
        assert config.greeks.risk_free_rate == 0.05

    def test_greeks_enabled(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo:\n  greeks:\n    enabled: true\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is True
        assert config.greeks.risk_free_rate == 0.05

    def test_custom_risk_free_rate(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nyahoo:\n  greeks:\n    enabled: true\n    risk_free_rate: 0.04\n"
        )
        config = load_config(config_path=rc)
        assert config.greeks.risk_free_rate == 0.04

    def test_greeks_not_parsed_for_tradier(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: tradier\ntradier:\n  api_key: abc\n  greeks:\n    enabled: true\n"
        )
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False

    def test_greeks_with_provider_override(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\nyahoo:\n  greeks:\n    enabled: true\n")
        config = load_config(config_path=rc, provider_override="yahoo")
        assert config.greeks.enabled is True

    def test_greeks_missing_section_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo: {}\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False
        assert config.greeks.risk_free_rate == 0.05

    def test_greeks_invalid_section_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nyahoo:\n  greeks: not_a_dict\n")
        config = load_config(config_path=rc)
        assert config.greeks.enabled is False


class TestRefreshConfig:
    def test_defaults_when_no_config(self, tmp_path):
        config = load_config(config_path=tmp_path / "nonexistent")
        assert config.refresh.regular == 60
        assert config.refresh.extended == 120
        assert config.refresh.closed == 300

    def test_custom_refresh_intervals(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nrefresh:\n  regular: 5\n  extended: 30\n  closed: 600\n"
        )
        config = load_config(config_path=rc)
        assert config.refresh.regular == 5
        assert config.refresh.extended == 30
        assert config.refresh.closed == 600

    def test_partial_refresh_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nrefresh:\n  regular: 10\n")
        config = load_config(config_path=rc)
        assert config.refresh.regular == 10
        assert config.refresh.extended == 120
        assert config.refresh.closed == 300

    def test_invalid_refresh_uses_defaults(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text("---\ndefault: yahoo\nrefresh: not_a_dict\n")
        config = load_config(config_path=rc)
        assert config.refresh == RefreshConfig()

    def test_refresh_with_provider_override(self, tmp_path):
        rc = tmp_path / "config.yaml"
        rc.write_text(
            "---\ndefault: yahoo\nrefresh:\n  regular: 15\n  extended: 45\n  closed: 120\n"
        )
        config = load_config(config_path=rc, provider_override="yahoo")
        assert config.refresh.regular == 15
        assert config.refresh.extended == 45
        assert config.refresh.closed == 120
