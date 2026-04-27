# Configuration

TenorTUI loads YAML from `~/.config/tenor/config.yaml` (with `~/.tenorrc` as
a fallback). Every option is also discoverable via:

```bash
tenortui --config-help
```

## Example config.yaml

```yaml
default: yahoo

yahoo:
  greeks:
    enabled: true
    risk_free_rate: 0.04

tradier:
  api_key: ""
  sandbox: false

spread_thresholds:
  tight: 3.0
  moderate: 10.0

refresh:
  regular: 60
  extended: 120
  closed: 300

fred_api_key: ""
```

## All options

| Key | Type | Default | Description |
|---|---|---|---|
| `default` | string | `yahoo` | Default data provider. Options: `yahoo`, `tradier` |
| `yahoo.greeks.enabled` | bool | `false` | Enable client-side Greeks calculation (Black-Scholes / Binomial) |
| `yahoo.greeks.risk_free_rate` | float | `0.05` | Risk-free rate for Greeks (decimal). Fallback when live FRED rate unavailable |
| `tradier.api_key` | string | (required) | Tradier API key. Required when `default: tradier` |
| `tradier.sandbox` | bool | `false` | Use Tradier sandbox endpoint instead of production |
| `spread_thresholds.tight` | float | `5.0` | Bid-ask spread % below this is highlighted green |
| `spread_thresholds.moderate` | float | `15.0` | Bid-ask spread % below this is yellow; above is red |
| `refresh.regular` | int | `60` | Auto-refresh interval (seconds) during regular market hours |
| `refresh.extended` | int | `120` | Auto-refresh interval (seconds) during pre-market / after-hours |
| `refresh.closed` | int | `300` | Auto-refresh interval (seconds) when the market is closed |
| `fred_api_key` | string | `""` | FRED API key for fetching live risk-free rate (optional) |

## CLI flags

CLI flags override config file values for the current run.

| Flag | Description |
|---|---|
| `--provider <name>` | Override the configured provider (`yahoo`, `tradier`, or `fixture`) |
| `--config-help` | Print all available config options and exit |
| `--help` | Print the full CLI help and exit |

## Where data lives

| Path | Purpose |
|---|---|
| `~/.config/tenor/config.yaml` | Configuration |
| `~/.config/tenor/history.json` | Recently viewed tickers (max 10) |
| `~/.config/tenor/watchlists.json` | Named watchlists |
