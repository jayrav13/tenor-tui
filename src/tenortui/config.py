from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tenortui.exceptions import ConfigError

KNOWN_PROVIDERS = {"yahoo", "tradier"}
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tenor" / "config.yaml"
LEGACY_CONFIG_PATH = Path.home() / ".tenorrc"

PROVIDER_REQUIRED_FIELDS: dict[str, list[str]] = {
    "yahoo": [],
    "tradier": ["api_key"],
}


def resolve_config_path(
    new_path: Path = DEFAULT_CONFIG_PATH,
    legacy_path: Path = LEGACY_CONFIG_PATH,
) -> Path:
    """Return new_path if it exists, fall back to legacy_path if it exists, else new_path."""
    if new_path.exists():
        return new_path
    if legacy_path.exists():
        return legacy_path
    return new_path


@dataclass
class SpreadThresholds:
    tight: float = 5.0
    moderate: float = 15.0


@dataclass
class GreeksConfig:
    enabled: bool = False
    risk_free_rate: float = 0.05


@dataclass
class AppConfig:
    provider_name: str
    provider_config: dict = field(default_factory=dict)
    spread_thresholds: SpreadThresholds = field(default_factory=SpreadThresholds)
    greeks: GreeksConfig = field(default_factory=GreeksConfig)
    fred_api_key: str | None = None


def _parse_greeks_config(provider_name: str, provider_config: dict) -> GreeksConfig:
    """Parse greeks config from provider section. Only applies to Yahoo."""
    if provider_name != "yahoo":
        return GreeksConfig()
    section = provider_config.get("greeks")
    if not isinstance(section, dict):
        return GreeksConfig()
    return GreeksConfig(
        enabled=bool(section.get("enabled", False)),
        risk_free_rate=float(section.get("risk_free_rate", 0.05)),
    )


def _parse_spread_thresholds(raw: dict) -> SpreadThresholds:
    """Parse spread_thresholds from raw config, falling back to defaults."""
    section = raw.get("spread_thresholds")
    if not isinstance(section, dict):
        return SpreadThresholds()
    return SpreadThresholds(
        tight=float(section.get("tight", 5.0)),
        moderate=float(section.get("moderate", 15.0)),
    )


def load_config(
    config_path: Path | None = None,
    provider_override: str | None = None,
) -> AppConfig:
    if config_path is None:
        config_path = resolve_config_path()
    raw = _read_config_file(config_path)
    spread_thresholds = _parse_spread_thresholds(raw)
    fred_api_key = raw.get("fred_api_key")

    if provider_override:
        provider_name = provider_override
        # When overriding via CLI, skip required-field validation — caller is
        # responsible for supplying credentials (env vars, etc.)
        provider_config = raw.get(provider_name, {}) or {}
        if provider_name not in KNOWN_PROVIDERS:
            raise ConfigError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {', '.join(sorted(KNOWN_PROVIDERS))}"
            )
        return AppConfig(
            provider_name=provider_name,
            provider_config=provider_config,
            spread_thresholds=spread_thresholds,
            greeks=_parse_greeks_config(provider_name, provider_config),
            fred_api_key=fred_api_key,
        )

    if "default" in raw:
        provider_name = raw["default"]
    else:
        provider_keys = [k for k in raw if k in KNOWN_PROVIDERS]
        provider_name = provider_keys[0] if provider_keys else "yahoo"

    if provider_name not in KNOWN_PROVIDERS:
        raise ConfigError(
            f"Unknown provider '{provider_name}'. "
            f"Available: {', '.join(sorted(KNOWN_PROVIDERS))}"
        )

    provider_config = raw.get(provider_name, {}) or {}

    for req_field in PROVIDER_REQUIRED_FIELDS.get(provider_name, []):
        if req_field not in provider_config:
            raise ConfigError(
                f"Provider '{provider_name}' requires '{req_field}' in ~/.config/tenor/config.yaml"
            )

    return AppConfig(
        provider_name=provider_name,
        provider_config=provider_config,
        spread_thresholds=spread_thresholds,
        greeks=_parse_greeks_config(provider_name, provider_config),
        fred_api_key=fred_api_key,
    )


def _read_config_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse {path}: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file {path} must be a YAML mapping, got {type(data).__name__}"
        )
    return data
