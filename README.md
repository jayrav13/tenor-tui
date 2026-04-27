# TenorTUI

[![PyPI](https://img.shields.io/pypi/v/tenor-tui.svg?v=1)](https://pypi.org/project/tenor-tui/)
[![CI](https://github.com/jayrav13/tenor-tui/actions/workflows/ci.yml/badge.svg)](https://github.com/jayrav13/tenor-tui/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/tenor-tui.svg?v=1)](https://pypi.org/project/tenor-tui/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A terminal UI for browsing stock options chains. Live quotes, full options
chains with Greeks, named watchlists, pluggable data providers — all in
your terminal.

**Documentation, screenshots, and feature walkthrough:
<https://jayravaliya.com/tenor-tui/>**

![TenorTUI showing AAPL options chain](docs/site/docs/assets/snapshots/hero.svg)

## Install

```bash
pipx install tenor-tui     # recommended
pip install tenor-tui      # alternative
```

Then run `tenortui`.

Requires Python 3.11+. See [Installation](https://jayravaliya.com/tenor-tui/installation/)
for from-source setup and provider configuration.

## Develop

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
poetry install --with docs
pre-commit install && pre-commit install --hook-type pre-push
poetry run tenortui
```

Common commands:

```bash
poetry run python -m pytest -v        # tests
poetry run ruff check src/ tests/     # lint
poetry run ruff format src/ tests/    # format
make docs-serve                       # preview docs locally
make snapshots && make demos          # regenerate UI screenshots/GIFs
```

The full developer guide and contribution flow live in
[`CLAUDE.md`](CLAUDE.md).

## Contribute

Open an issue first (a checkbox-list of success criteria helps reviewers).
Branch off `main` with `fix/<issue-number>-<short-desc>`, reference the issue
in your commit messages (`Closes #N` or `Refs #N`), and update the docs
surfaces called out in `CLAUDE.md`'s Documentation Sync table.

Every PR must add a `CHANGELOG.md` entry under `[Unreleased]` (CI enforces
this). Version bumps trigger an automatic PyPI release on merge.

## License

[MIT](LICENSE).
