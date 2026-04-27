# Contributing

Contributions welcome! This page is a quick orientation; the canonical
contribution flow lives in
[`CLAUDE.md`](https://github.com/jayrav13/tenor-tui/blob/main/CLAUDE.md)
in the repo.

## Local setup

```bash
git clone https://github.com/jayrav13/tenor-tui.git
cd tenor-tui
poetry install --with docs
pre-commit install && pre-commit install --hook-type pre-push
poetry run tenortui
```

## Running tests

```bash
poetry run python -m pytest -v               # full suite
poetry run python -m pytest tests/test_xyz.py # one file
poetry run python -m pytest -k some_test     # by name
```

## Linting and formatting

```bash
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
```

The pre-commit hooks run `ruff check --fix` and `ruff format` on staged files
automatically.

## Working on the docs

The docs site lives under `docs/site/`. To preview changes locally:

```bash
make docs-serve
```

To regenerate screenshots and demo GIFs (after a UI change):

```bash
make snapshots
make demos
```

VHS (`brew install vhs`) is required for `make demos`.

## Issue and PR conventions

- Open an issue first; a checkbox-list of success criteria helps reviewers.
- Branch off `main` with `fix/<issue-number>-<short-desc>`.
- Reference the issue (`Closes #N` or `Refs #N`) in commit messages.
- The project uses merge commits, not squash.

## License

MIT.
