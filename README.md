# TenorTUI

A terminal UI for browsing stock options chains with pluggable data providers.

## Install

```bash
pip install .
```

## Usage

```bash
tenortui                    # Uses Yahoo Finance (default, no config needed)
tenortui --provider tradier # Use Tradier (requires API key in config)
```

## Configuration

Create `~/.config/tenor/config.yaml` (optional):

```yaml
---
default: yahoo

yahoo: {}

tradier:
  api_key: your-api-key-here
  sandbox: false
```

Legacy `~/.tenorrc` is also supported as a fallback.

## Keybindings

| Key | Action |
|-----|--------|
| `/` or `s` | Focus search |
| `Enter` | Search ticker |
| `Ctrl+R` | Refresh data |
| `Left/Right` | Switch expiration |
| `Tab` | Cycle calls/puts |
| `q` | Quit |

## Data Providers

| Provider | API Key Required | Greeks |
|----------|-----------------|--------|
| Yahoo Finance | No | No |
| Tradier | Yes | Yes |

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -v
```
