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
class RefreshConfig:
    regular: int = 60
    extended: int = 120
    closed: int = 300


@dataclass
class AppConfig:
    provider_name: str
    provider_config: dict = field(default_factory=dict)
    spread_thresholds: SpreadThresholds = field(default_factory=SpreadThresholds)
    greeks: GreeksConfig = field(default_factory=GreeksConfig)
    fred_api_key: str | None = None
    refresh: RefreshConfig = field(default_factory=RefreshConfig)


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


def _parse_refresh_config(raw: dict) -> RefreshConfig:
    """Parse refresh intervals from raw config, falling back to defaults."""
    section = raw.get("refresh")
    if not isinstance(section, dict):
        return RefreshConfig()
    return RefreshConfig(
        regular=int(section.get("regular", 60)),
        extended=int(section.get("extended", 120)),
        closed=int(section.get("closed", 300)),
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
    refresh = _parse_refresh_config(raw)
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
            refresh=refresh,
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
        refresh=refresh,
    )


@dataclass
class ConfigOption:
    key: str
    type_name: str
    default: str
    description: str
    condition: str = ""


CONFIG_OPTIONS: list[ConfigOption] = [
    ConfigOption(
        key="default",
        type_name="str",
        default="yahoo",
        description="Default data provider. Options: yahoo, tradier.",
    ),
    ConfigOption(
        key="yahoo.greeks.enabled",
        type_name="bool",
        default="false",
        description="Enable client-side Greeks calculation using Black-Scholes/Binomial models.",
        condition="Only when provider is yahoo.",
    ),
    ConfigOption(
        key="yahoo.greeks.risk_free_rate",
        type_name="float",
        default="0.05",
        description="Risk-free interest rate for Greeks calculation (decimal, e.g. 0.05 = 5%). Used as fallback when live FRED rate is unavailable.",
        condition="Only when yahoo.greeks.enabled is true.",
    ),
    ConfigOption(
        key="tradier.api_key",
        type_name="str",
        default="required",
        description="Tradier API key for authentication.",
        condition="Required when provider is tradier.",
    ),
    ConfigOption(
        key="tradier.sandbox",
        type_name="bool",
        default="false",
        description="Use Tradier sandbox API endpoint instead of production.",
        condition="Only when provider is tradier.",
    ),
    ConfigOption(
        key="spread_thresholds.tight",
        type_name="float",
        default="5.0",
        description="Bid-ask spread percentage threshold for tight spread highlighting (green).",
    ),
    ConfigOption(
        key="spread_thresholds.moderate",
        type_name="float",
        default="15.0",
        description="Bid-ask spread percentage threshold for moderate spread highlighting (yellow). Spreads above this are red.",
    ),
]


def print_config_help(config_path: Path | None = None) -> None:
    if config_path is None:
        config_path = resolve_config_path()
    exists = config_path.exists()

    lines = [
        "TenorTUI Configuration Help",
        "=" * 28,
        "",
        "Config file: ~/.config/tenor/config.yaml",
    ]
    if exists:
        lines.append(f"Active config: {config_path} (exists)")
    else:
        lines.append(f"Active config: {config_path} (not found, using defaults)")
    lines.append("")
    lines.append("Options:")
    lines.append("-" * 8)
    lines.append("")

    # Group options by prefix for indented display
    current_section: list[str] = []
    for opt in CONFIG_OPTIONS:
        parts = opt.key.split(".")
        if len(parts) == 1:
            # Top-level option
            current_section = []
            default_str = (
                f'default: "{opt.default}"'
                if opt.type_name == "str"
                else f"default: {opt.default}"
            )
            lines.append(f"{opt.key} ({opt.type_name}, {default_str})")
            lines.append(f"  {opt.description}")
            if opt.condition:
                lines.append(f"  {opt.condition}")
            lines.append("")
        else:
            # Nested option — show section headers as needed
            section_parts = parts[:-1]
            leaf = parts[-1]
            indent = ""
            for i, section in enumerate(section_parts):
                if i >= len(current_section) or current_section[i] != section:
                    indent = "  " * i
                    lines.append(f"{indent}{section}:")
                    current_section = section_parts[: i + 1]
            indent = "  " * len(section_parts)
            default_str = (
                f'default: "{opt.default}"'
                if opt.type_name == "str"
                else f"default: {opt.default}"
            )
            if opt.default == "required":
                default_str = "required"
            lines.append(f"{indent}{leaf} ({opt.type_name}, {default_str})")
            lines.append(f"{indent}  {opt.description}")
            if opt.condition:
                lines.append(f"{indent}  {opt.condition}")
            lines.append("")

    lines.append("Example config:")
    lines.append("-" * 15)
    lines.append("default: yahoo")
    lines.append("yahoo:")
    lines.append("  greeks:")
    lines.append("    enabled: true")
    lines.append("    risk_free_rate: 0.04")
    lines.append("spread_thresholds:")
    lines.append("  tight: 3.0")
    lines.append("  moderate: 10.0")

    print("\n".join(lines))


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
