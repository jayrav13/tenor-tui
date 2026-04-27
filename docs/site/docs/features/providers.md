# Providers

TenorTUI is provider-agnostic: any class implementing the `DataProvider`
protocol can be plugged in. Two are included.

## Capability matrix

| Capability | Yahoo (default) | Tradier |
|---|---|---|
| Quotes | ✅ | ✅ |
| Expirations | ✅ | ✅ |
| Options chain | ✅ | ✅ |
| Implied volatility | ✅ | ✅ |
| Greeks (Δ Γ Θ ν ρ) | ❌ | ✅ |
| Authentication required | None | API key |

## Yahoo Finance (default)

No setup. The default provider uses the [yfinance](https://pypi.org/project/yfinance/)
library and works out of the box.

```bash
tenortui
# equivalent to
tenortui --provider yahoo
```

## Tradier

Requires a [Tradier](https://tradier.com/) account and API key. Add to
`~/.config/tenor/config.yaml`:

```yaml
provider: tradier
tradier:
  api_key: "YOUR_KEY_HERE"
  endpoint: "sandbox"  # or "production"
```

Then launch:

```bash
tenortui --provider tradier
```

## Fixture (development only)

A deterministic provider used for screenshots and demos. Returns frozen data
for AAPL and a placeholder for other symbols. Useful when you want a
reproducible UI state without making network calls.

```bash
tenortui --provider fixture
```

## Adding a new provider

Implement the `DataProvider` protocol from `src/tenortui/providers/base.py`:

```python
from typing import Protocol
from tenortui.models import Quote, OptionsChain

class DataProvider(Protocol):
    name: str
    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
```

Then register it in `src/tenortui/providers/__init__.py`'s `PROVIDERS` dict.
The CLI flag `--provider <name>` will pick it up.

See [Contributing](../contributing.md) for the dev workflow.
