# Stable Product Shipping — Design

**Date:** 2026-04-26
**Status:** Draft, awaiting user review

## Goal

Ship TenorTUI as a stable, installable, properly-documented open-source product. Mirror the conventions established in `jayrav13/njtransit` (Ruby gem) and `jayrav13/ruby-pure-greeks` (Ruby gem) so the user's open-source projects share a consistent shape.

## Motivation

TenorTUI currently looks like a hobby repo: no package on PyPI, no release automation, no changelog, README is feature-walkthrough heavy, no docs site. The user is building out their personal site (`jayrav13.github.io` → `jayravaliya.com`) as a portfolio of stable shipped projects. TenorTUI should join `njtransit` and `pure_greeks` as a "this is a real product, here's how to use it" entry on that site. This design covers the work to make TenorTUI ready for that.

## Success Criteria

- `pip install tenor-tui` (or `pipx install tenor-tui`) works from PyPI
- `https://jayravaliya.com/tenor-tui/` serves a feature walkthrough with embedded SVG screenshots and VHS-generated GIFs
- `README.md` is dev/install/contribute-focused; feature walkthroughs live on the docs site
- `CLAUDE.md` has a Documentation Sync table that prevents future doc drift
- `CHANGELOG.md` exists and every PR going forward bumps the version + adds an entry (CI-enforced)
- A merge to `main` triggers a release workflow that publishes to PyPI via Trusted Publishing (OIDC) and creates a GitHub Release with the wheel attached
- A merge to `main` that touches the docs site triggers a docs deploy workflow that pushes to `gh-pages`

## Out of Scope

- Adding the project page on `jayrav13.github.io` (deferred — will be a one-line offer when this lands)
- Any feature work (no new TUI behavior, no new providers, no new keybindings) — this is purely shipping infrastructure
- Migrating existing watchlist/history persistence formats (none of this work touches `~/.config/tenor/`)

## Components

Six discrete pieces, each ownable independently.

### 1. PyPI Packaging Hardening (`pyproject.toml`)

Update `pyproject.toml` to include the metadata PyPI requires for a polished project page:

- Add `[project]` block (in addition to or replacing `[tool.poetry]`, depending on Poetry version) with:
  - `license = { text = "MIT" }` — and add `LICENSE` file at repo root
  - `authors = [{ name = "Jay Ravaliya", email = "jayrav13@gmail.com" }]`
  - `urls.Homepage = "https://jayravaliya.com/tenor-tui/"`
  - `urls.Documentation = "https://jayravaliya.com/tenor-tui/"`
  - `urls.Source = "https://github.com/jayrav13/tenor-tui"`
  - `urls.Issues = "https://github.com/jayrav13/tenor-tui/issues"`
  - `urls.Changelog = "https://github.com/jayrav13/tenor-tui/blob/main/CHANGELOG.md"`
  - `classifiers` — Development Status, Intended Audience (End Users / Developers / Financial), License, Programming Language :: Python :: 3.11, 3.12, 3.13, Topic :: Office/Business :: Financial :: Investment, Environment :: Console :: Curses
  - `keywords = ["options", "stocks", "tui", "terminal", "trading", "finance"]`
  - `requires-python = ">=3.11"`
- Verify `poetry build` produces a clean wheel
- Verify the rendered PyPI long description (the README) doesn't have broken local image links — if any are present, switch to absolute GitHub raw URLs

**Risk:** PyPI may already have a project named `tenor-tui`. Step 0 in the implementation plan is to verify availability at `https://pypi.org/project/tenor-tui/` (404 = available). Fallbacks if taken: `tenortui`, `tenor`, `tenor-cli`.

### 2. Release Automation (`.github/workflows/release.yml`)

A new workflow that publishes to PyPI on merge to `main`, only when the version has changed.

- **Trigger:** `push: { branches: [main] }`
- **Job 1 — `should-release`** (no permissions): extracts version from `pyproject.toml`, checks if a git tag `v<version>` already exists, sets an output `needs_release` accordingly
- **Job 2 — `release`** (`needs: should-release`, `if: needs.should-release.outputs.needs_release == 'true'`):
  - `permissions: { contents: write, id-token: write }`
  - `environment: release` (the GitHub environment configured for PyPI Trusted Publishing)
  - Steps:
    1. Checkout
    2. Setup Python 3.11
    3. Install Poetry
    4. `poetry install --without dev` and run a smoke import
    5. `poetry build` → produces `dist/tenor_tui-<version>-py3-none-any.whl` and `dist/tenor_tui-<version>.tar.gz`
    6. `pypa/gh-action-pypi-publish@release/v1` (uses OIDC, no token needed)
    7. `git tag v<version> && git push origin v<version>`
    8. `gh release create v<version> dist/* --notes-file <notes>` where `<notes>` is the CHANGELOG section between `## [<version>]` and the next `## [` heading (extracted by a small `bin/changelog-section` script, also invoked by the workflow)

**Pre-requisite (manual, one-time, completed by user):** Trusted Publisher created on PyPI side and matching `release` environment created on the `jayrav13/tenor-tui` GitHub repo.

### 3. Versioning + CHANGELOG Discipline

#### CHANGELOG.md

New file at repo root, Keep-a-Changelog format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-04-26

### Added
- Initial public release with watchlists, options chain, Yahoo + Tradier providers
- PyPI distribution
- GitHub Pages docs site
```

The 1.0.0 entry serves as the "we're stable" line in the sand.

#### `bin/check-version-bump`

New Python script, called by CI on PRs:

1. Diff `pyproject.toml`'s `version` field against `origin/main`
2. If author is `dependabot[bot]` → exit 0
3. If `version` is unchanged → fail with a message linking to `CLAUDE.md`'s Git Workflow section
4. If `version` is changed → check `CHANGELOG.md` `[Unreleased]` section is non-empty, otherwise fail

Wired into `.github/workflows/ci.yml` as a new job `check-version-bump`, runs on `pull_request`.

#### Versioning rules (SemVer)

- **Patch** (0.1.x → 0.1.x+1): bug fixes, doc-only updates, internal refactors with tests
- **Minor** (0.1.x → 0.2.0): new features, new providers, new keybindings, new config options
- **Major** (0.x.y → 1.0.0): breaking changes (config schema removals, removed CLI flags, dropped Python versions)

This shipping push lands as **1.0.0** — the first major is the explicit "we're stable" signal.

### 4. Docs Site (`docs/site/`)

MkDocs Material project, deployed to GitHub Pages, served at `https://jayravaliya.com/tenor-tui/`.

#### File layout

```
docs/site/
├── mkdocs.yml
└── docs/
    ├── index.md              # Hero shot, one-line pitch, install one-liner, quick start
    ├── installation.md       # pipx (recommended), pip, from source; Python version requirements
    ├── quickstart.md         # Launch, search a ticker, browse a chain, add to watchlist
    ├── features/
    │   ├── options-chain.md  # Calls/puts table, ATM marker, expiry tabs, Greeks columns
    │   ├── watchlists.md     # Named lists, equity + options, w/W/d/S keys, sorting
    │   ├── providers.md      # Yahoo (default) vs Tradier (API key), capability matrix
    │   └── keybindings.md    # Full key reference table
    ├── configuration.md      # ~/.config/tenor/config.yaml, every option, --config-help
    ├── contributing.md       # Brief — points back to README's Develop section + repo CONTRIBUTING flow
    └── assets/
        ├── snapshots/        # Generated SVGs from bin/snapshot
        └── demos/            # Generated GIFs from VHS tapes
```

#### `mkdocs.yml` highlights

- `theme.name: material`
- `theme.features: [navigation.tabs, navigation.instant, content.code.copy, navigation.top]`
- `theme.palette` with light + dark schemes and a toggle
- `site_url: https://jayravaliya.com/tenor-tui/`
- `repo_url: https://github.com/jayrav13/tenor-tui`
- `repo_name: jayrav13/tenor-tui`
- `plugins: [search, social]` — `social` auto-generates Open Graph cards
- `markdown_extensions: [admonition, pymdownx.superfences, pymdownx.tabbed, pymdownx.details, attr_list, md_in_html]`

#### Asset generation

**SVG snapshots** — `bin/snapshot` (Python script):

- Imports the Textual app, configures it with a deterministic `FixtureProvider` (frozen prices, fixed expirations, predictable Greeks)
- Drives the app to specific states via Textual's `Pilot` API (key presses, text input, waiting for messages)
- At each state, calls `app.save_screenshot()` and writes the SVG into `docs/site/docs/assets/snapshots/`
- Snapshot definitions are declared in a small in-script registry: `(name, async function that drives the app)`
- Idempotent — running it twice produces identical SVGs (deterministic fixture data is the key)

**VHS demos** — `docs/tapes/*.tape` files:

- One tape per demo, scripts terminal interaction (key presses, sleeps, output settings)
- Standardize on a single nerd font and consistent dimensions (`Set FontSize 14`, `Set Width 1200`, `Set Height 700`) across all tapes for visual consistency
- `make demos` runs `vhs` over each tape, outputs to `docs/site/docs/assets/demos/`
- Initial set:
  1. `tape/launch-and-search.tape` — boot, type AAPL, see chain
  2. `tape/watchlist-flow.tape` — `w` to open picker, add a symbol, switch list
  3. `tape/expiry-and-greeks.tape` — switch expiry tabs, scroll the chain

**Determinism risk:** the TUI shows live prices that change every run. The `FixtureProvider` used by both snapshots and tapes returns frozen, predictable data so SVGs/GIFs don't churn on every regeneration. This fixture lives at `src/tenortui/providers/fixture.py`, is registered in `providers/__init__.py` like any other provider, and is selected via `--provider fixture`. Tapes invoke `tenortui --provider fixture`; the snapshot script imports the app and constructs it with the fixture directly.

#### Docs deploy workflow (`.github/workflows/docs.yml`)

- **Trigger:** `push: { branches: [main], paths: ['docs/site/**'] }` plus `workflow_dispatch`
- **Permissions:** `contents: write` (to push to `gh-pages`)
- **Steps:**
  1. Checkout
  2. Setup Python 3.11
  3. `pip install mkdocs-material "mkdocs-material[imaging]"` (the imaging extra is needed for social cards)
  4. `cd docs/site && mkdocs gh-deploy --force --remote-branch gh-pages`
- GitHub Pages is configured (one-time, manual via repo settings) to serve from the `gh-pages` branch

### 5. README Rewrite

Strip out feature walkthroughs (those move to docs site). New shape:

```markdown
# TenorTUI

[![PyPI](https://img.shields.io/pypi/v/tenor-tui.svg)](https://pypi.org/project/tenor-tui/)
[![CI](https://github.com/jayrav13/tenor-tui/actions/workflows/ci.yml/badge.svg)](...)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/tenor-tui.svg)](https://pypi.org/project/tenor-tui/)

A terminal UI for browsing stock options chains. Live quotes, full options chains
with Greeks, named watchlists, and pluggable data providers.

**Documentation, screenshots, and feature walkthrough: https://jayravaliya.com/tenor-tui/**

![Hero screenshot](docs/site/docs/assets/snapshots/hero.svg)

## Install

    pipx install tenor-tui     # recommended
    pip install tenor-tui      # alternative

## Quick start

    tenortui

## Develop

[clone, poetry install, poetry run pytest, poetry run ruff, pre-commit setup]

## Contribute

[issue/PR flow, link to CLAUDE.md]

## License

MIT
```

Total target: under 80 lines.

### 6. CLAUDE.md Updates

#### Documentation Sync section (new, near the top)

Lead paragraph (mirrors njtransit's framing):

> Any change that affects public behavior, configuration, dependencies, or the release process **must** update every relevant doc surface **in the same PR**. Docs that go stale silently are worse than docs that are missing — readers learn not to trust them.

Followed by this table:

| Change | Update |
|---|---|
| New or changed public CLI flag (`tenortui --foo`) | `README.md` Quick start, `docs/site/docs/installation.md` or `quickstart.md`, `CHANGELOG.md` |
| New or changed config option (`config.yaml`) | `src/tenortui/config.py` `CONFIG_OPTIONS` registry, `docs/site/docs/configuration.md`, `CHANGELOG.md` |
| New keybinding | `docs/site/docs/features/keybindings.md`, the relevant feature page, `CHANGELOG.md` |
| New widget or visible UI flow | `docs/site/docs/features/<area>.md`, regenerate affected snapshots/tapes, `CHANGELOG.md` |
| New or changed provider capability | `docs/site/docs/features/providers.md` capability matrix, `CHANGELOG.md` |
| New or changed `DataProvider` protocol method | `CLAUDE.md` Architecture section, `docs/site/docs/features/providers.md`, `CHANGELOG.md` |
| New `bin/` script | `README.md` Develop section, `CLAUDE.md` Commands section, `CHANGELOG.md` |
| Dependency added/removed/version-bumped | `pyproject.toml`, `CHANGELOG.md` if user-visible |
| CI workflow change | `.github/workflows/ci.yml`, `README.md` Develop section if it changes the user-facing flow |
| Release workflow change | `.github/workflows/release.yml`, `CLAUDE.md` Git Workflow section if process changes |
| Docs site theme/structure change | `docs/site/mkdocs.yml`, `CLAUDE.md` if the IA shifts |
| Git workflow change (issue/branch/commit conventions) | `CLAUDE.md` Git Workflow section |
| Refactor / internal cleanup with no behavior change | None — but note in PR description so it's intentional |

#### Git Workflow updates

- Add a new step "Bump version + CHANGELOG entry" between Implement and Commit
- Add a new step "Monitor Release" after Merge (with `bin/release-watch` analogous to `bin/ci-watch`)

#### Sibling Pages registry reminder

New short section noting that `jayrav13/jayrav13.github.io`'s CLAUDE.md maintains a registry of sibling Pages-enabled repos, and that `tenor-tui` must be listed there once the docs site is live (path: `/tenor-tui/*`).

## Architecture / Boundaries

Each component is independently shippable and has clear boundaries:

- **PyPI metadata** — pure config change; affects nothing at runtime
- **Release workflow** — fires only on version-bump merges; gated by tag-existence check
- **Docs deploy workflow** — fires only on `docs/site/**` paths; failures don't block other workflows
- **Snapshot/tape scripts** — live in `bin/` and `docs/tapes/`; output to `docs/site/docs/assets/`; not invoked by CI (run by hand when UI changes)
- **`FixtureProvider`** — implements the `DataProvider` protocol like any other provider; lives next to `yahoo.py` and `tradier.py`; selectable via `--provider fixture`
- **`check-version-bump`** — pure CLI script that reads git + files; no app dependency

## Testing Strategy

- **`pyproject.toml` changes:** `poetry build && python -m twine check dist/*` to verify wheel is PyPI-acceptable
- **Release workflow:** dry-run via `act` or by pointing the workflow at TestPyPI for the first run; gate the real PyPI publish behind a manual approval on the first execution
- **`check-version-bump`:** unit-test the script with subprocess mocks
- **Docs build:** add a `docs-build` job to `ci.yml` that runs `mkdocs build --strict` (catches broken links and missing assets)
- **`FixtureProvider`:** unit test that it returns deterministic data; snapshot script smoke-test that it produces SVGs successfully
- **README rendering:** preview via `python -m readme_renderer README.md` to catch PyPI rendering issues

## Risks & Open Items

1. **PyPI name `tenor-tui` may be taken.** Verify before any other work. If taken, fallback ranking: `tenortui`, `tenor`, `tenor-cli`. Updating the name later is painful — do this first.
2. **Snapshot/tape determinism.** Live prices break reproducibility. Mitigated by the `FixtureProvider`. If we ever add features that depend on real network calls (rare-event flows), those won't get snapshots — and that's fine.
3. **VHS font/dimensions consistency.** All tapes must use identical settings or the GIFs will look mismatched on the site. Standardize at the start; add a `docs/tapes/_common.tape` or document the required prelude.
4. **First release tag conflict.** If `v1.0.0` already exists in the repo (it doesn't today, but worth checking), the release workflow's tag-existence check prevents accidental re-release.
5. **GitHub Pages CNAME / DNS coordination.** `tenor-tui` repo's `gh-pages` branch needs to serve at `jayravaliya.com/tenor-tui/`. This requires (a) GitHub Pages enabled on the repo with source = `gh-pages` branch, and (b) the user-pages site at `jayravaliya.com` having no conflicting top-level route named `tenor-tui` (per its CLAUDE.md). Verify both before deploying.
6. **Docs site `[imaging]` extra requires Cairo.** MkDocs Material's social-card plugin needs Cairo system libraries. The docs deploy workflow must `apt-get install` them on the runner. If this is a hassle, drop social cards (or use the lightweight version).

## Manual Prerequisites (User Actions)

Before implementation can run end to end, the user (Jay) must complete:

- [x] Create PyPI Trusted Publisher pointing at `jayrav13/tenor-tui` + `release.yml` + `release` environment (done 2026-04-26)
- [ ] Create GitHub Environment named `release` on the `tenor-tui` repo (Settings → Environments → New environment)
- [ ] Verify `tenor-tui` name availability on PyPI (check `https://pypi.org/project/tenor-tui/`)
- [ ] After docs site lands: enable GitHub Pages on the repo (Settings → Pages → Source: `gh-pages` branch)
- [ ] After docs site lands: add `tenor-tui` to the sibling-Pages registry in `jayrav13.github.io`'s CLAUDE.md

## Implementation Order (Suggested)

1. **Step 0:** Verify PyPI name availability
2. **PyPI metadata + LICENSE** (small, no risk)
3. **CHANGELOG.md + version 1.0.0 in pyproject.toml**
4. **`bin/check-version-bump` + CI job**
5. **Release workflow** — first run publishes 1.0.0
6. **README rewrite** (depends on knowing the PyPI URL works)
7. **`FixtureProvider`** (needed by snapshot/tape scripts)
8. **Snapshot script + initial SVGs**
9. **VHS tapes + initial GIFs**
10. **MkDocs site + content** (uses the assets from steps 8–9)
11. **Docs deploy workflow + GitHub Pages enablement**
12. **CLAUDE.md updates** — last, so all referenced files exist

The `writing-plans` skill will refine this into the actual plan.
