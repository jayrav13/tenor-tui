# Installation

TenorTUI requires **Python 3.11 or newer**.

## Recommended: pipx

[pipx](https://pipx.pypa.io/) installs Python apps in isolated environments
and puts the entry-point on your `PATH`.

```bash
pipx install tenor-tui
```

Then run:

```bash
tenortui
```

## Alternative: pip

```bash
pip install --user tenor-tui
```

You may need to add `~/.local/bin` to your `PATH` for the `tenortui` command
to be found.

## From source

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
poetry install
poetry run tenortui
```

## Configuration directory

On first launch, TenorTUI creates `~/.config/tenor/`:

- `config.yaml` — provider selection, theme, etc.
- `history.json` — recently viewed tickers
- `watchlists.json` — your watchlists

See [Configuration](configuration.md) for the full list of options.

## Choosing a provider

The default provider is **Yahoo Finance** — no API key required, no signup.

If you have a [Tradier](https://tradier.com/) account, you can use the Tradier
provider for richer Greeks data:

```bash
tenortui --provider tradier
```

See [Providers](features/providers.md) for the full comparison.
