# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation

- Added Claude Code subagent definitions under `.claude/agents/` (project
  manager, software engineer, code reviewer, CI watcher) and documented the
  agent-driven issue -> PR -> review -> CI -> merge workflow, including the
  3-issues-in-flight limit, in `CLAUDE.md`. The CLAUDE.md Planning rule now
  names the `docs/plans/<date>-<issue#>-<slug>.md` convention and states that
  a plan only in the PR body doesn't count (#65).

- `CLAUDE.md` now documents the GitHub Pages source-path requirement
  (`gh-pages` branch, root path `/`) and the diagnostic flow when the live
  site looks stale, after the silent-deploy trap surfaced during #53 (#55).

### Added

- `b` key and `:watchlist` / `:wl` command bring the watchlist panel back
  after a ticker is loaded, with fresh quotes and the list focused (#66).

### Fixed

- Watchlist quote refreshes (every auto-refresh cycle) no longer move focus
  to the hidden watchlist list, and `d` no longer deletes a watchlist entry
  while the panel is hidden. `b` focuses the list right away, so a refresh
  or a ticker load still running when it is pressed no longer leaves focus
  on the hidden chain (#66).
- A malformed delta filter in the command palette (e.g.
  `:filter delta 1.2.3 0.5`) crashed the app with a `ValueError`. The delta
  parser now accepts only real numbers, and an unrecognised or malformed
  filter shows an "Unknown filter" warning instead of being silently ignored
  and refetching the chain (#60).
- Pressing `d` in the watchlist panel could delete a different item from the
  highlighted one (and save that deletion) whenever the display order differed
  from insertion order, i.e. when items were grouped by symbol or re-sorted
  with `S`. It now removes exactly the highlighted row's item (#64).
- `Esc` in the settings screen now closes it when nothing is being
  edited, matching the documented modal behavior. With unsaved changes it
  shows the `:q! / :wq` warning instead of closing; in an inline edit or the
  command bar it still only cancels that (#68).
- Viewing a ticker no longer adds it to the active watchlist. Browsing used
  to append every loaded symbol with no cap, so curated lists filled up with
  everything you had looked at. Watchlists now change only when you press
  `w` (#67).
- `--provider fixture` was accepted by argparse but rejected at runtime with
  "Unknown provider 'fixture'". `KNOWN_PROVIDERS` was hardcoded to
  `{"yahoo", "tradier"}` and drifted from the `PROVIDERS` registry. It now
  derives from `PROVIDERS.keys()` so the two stay in sync. Also re-recorded
  the demo GIFs that were broken by this bug (#53).
- README PyPI/Python badges showed "package or version not found" because
  shields.io's CDN cached a 404 from before 1.0.0 was published. Added
  `?v=1` query string to bust the cache.

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
