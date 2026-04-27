# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project will adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once the first PyPI release ships.

Until then, entries land under `[Unreleased]` and roll into the first
versioned section at release time.

## [Unreleased]

### Added

- MkDocs Material documentation site at `docs/site/`, deployed to GitHub
  Pages on every merge to `main` (`.github/workflows/docs.yml`). Live at
  <https://jayravaliya.com/tenor-tui/>.
- `FixtureProvider` (`--provider fixture`) returning deterministic data for
  screenshots and demos.
- `bin/snapshot` — regenerates SVG screenshots from the live Textual app via
  the `Pilot` API, with hash + timestamp normalization for byte-stable output.
- VHS `.tape` files under `docs/tapes/` and three demo GIFs under
  `docs/site/docs/assets/demos/`.
- `Makefile` with `snapshots`, `demos`, `docs`, `docs-strict`, `docs-serve`
  targets.
- Optional `[tool.poetry.group.docs]` for MkDocs Material — installed via
  `poetry install --with docs`.
- `docs-build` CI job runs `mkdocs build --strict` on every PR.
- `CLAUDE.md` Documentation Sync section: every change must update its
  relevant doc surface in the same PR.
