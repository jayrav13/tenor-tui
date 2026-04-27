# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-04-27

First public PyPI release. Marks TenorTUI as a stable shipped product.

### Added

- **PyPI distribution.** `pip install tenor-tui` (or `pipx install`) works
  from PyPI.
- **MkDocs Material documentation site** at `docs/site/`, deployed to GitHub
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
- Full PyPI metadata in `pyproject.toml` (license, authors, URLs, classifiers,
  keywords) — wheel passes `twine check`.
- MIT `LICENSE` file at the repo root.
- `bin/check-version-bump` — CI gate that requires every PR to add a
  CHANGELOG `[Unreleased]` entry, or bump the version with a matching
  `[<version>]` section. Dependabot exempt.
- `.github/workflows/release.yml` — auto-publishes to PyPI via Trusted
  Publishing (OIDC) on merges that bump the version, then tags and creates
  a GitHub Release with the wheel + sdist attached.
- `bin/changelog-section` — extracts a `## [<version>]` section's body for
  use as GitHub Release notes.

### Changed

- README rewritten as a developer/install/contribute landing (under 80 lines,
  badges + install + dev workflow + contribute). Feature walkthroughs now
  live on the docs site.
