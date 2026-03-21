# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run the app
tenortui
tenortui --provider tradier

# Run all tests
python -m pytest -v

# Run a single test file or test
python -m pytest tests/test_models.py -v
python -m pytest tests/test_models.py::test_mid_price -v
```

## Architecture

TenorTUI is a Textual-based terminal app for browsing stock options chains. Python 3.11+, built with hatchling.

### Provider pattern

Data providers implement the `DataProvider` protocol (`providers/base.py`): `get_quote()`, `get_expirations()`, `get_chain()`. Providers are registered in `providers/__init__.py` via the `PROVIDERS` dict. Currently: Yahoo Finance (default, no auth) and Tradier (requires API key in config). A standalone `batch_quotes()` function in `yahoo.py` fetches multiple quotes in one API call for the Recently Viewed feature.

Provider methods are synchronous — the app wraps them with `asyncio.to_thread()` to keep the UI responsive.

### App flow

`TenorTUI` (app.py) orchestrates everything. On launch:
1. History is loaded from `~/.config/tenor/history.json`; if non-empty, `RecentlyViewed` is shown with live quotes fetched via `batch_quotes()`
2. On ticker submit (search bar or Recently Viewed selection), `_load_ticker` fetches quote + expirations, saves to history, populates `ExpirySelector` tabs
3. When an expiry tab is selected, `_load_chain` fetches and displays the options chain
4. Workers use `@work(exclusive=True, group=...)` — separate groups for ticker, chain, and recent quote loads
5. `_loading_ticker` flag prevents expiry tab events from firing during initial ticker load

### Widget hierarchy

- `TickerBar` — search input + quote display
- `RecentlyViewed` — `ListView` of recently viewed tickers with live prices; posts `TickerBar.TickerSubmitted` on selection
- `ExpirySelector` — `TabbedContent` with one tab per expiration date, posts `ExpirySelected` messages
- `ChainTable` — two `DataTable`s (calls/puts) inside a `VerticalScroll`, with ATM divider row and auto-scroll to ATM
- `StatusBar` — shows provider name and last refresh time

### Data models

`models.py` defines `Quote`, `OptionContract` (with optional Greeks), and `OptionsChain`. Greek columns appear dynamically when the provider supplies them.

### Configuration

`config.py` loads YAML from `~/.config/tenor/config.yaml` (falls back to `~/.tenorrc`). Provider can be overridden via `--provider` CLI flag. Each provider declares required fields in `PROVIDER_REQUIRED_FIELDS`.

### History

`history.py` manages recently viewed tickers in `~/.config/tenor/history.json` — a JSON array of symbols, max 10, most recent first.

### Styling

Textual CSS lives in `src/tenortui/styles/app.tcss`. Widgets also define `DEFAULT_CSS` inline.

### Testing

Tests use `FakeProvider` from `conftest.py` to avoid real API calls. `pytest-asyncio` is used for async test support.

## Planning

All design docs and implementation plans must be persisted to this repo (under `docs/`) and committed to the feature branch before creating a PR.

## Git Workflow

Every change follows this process: Issue -> Branch -> Commit -> PR -> Merge -> Cleanup.

### 1. Create Issue

- Create a GitHub issue describing the work
- Add the `claude` label to issues created by Claude
- For human-created issues: add `claude:reviewed` label after reviewing (not both labels on same issue)
- Include a **Success Criteria** section with testable checkbox items:
  ```markdown
  ## Success Criteria
  - [ ] Feature X works as described
  - [ ] All existing tests pass
  - [ ] New tests added for feature X
  ```
- Note `*Co-authored by Claude*` if applicable

### 2. Create Worktree & Branch

**Always use git worktrees** for feature work. This enables multiple concurrent sessions without conflicts.

```bash
# Use EnterWorktree tool to create an isolated worktree
# This creates a worktree at .claude/worktrees/<name>/ with a dedicated branch
```

Branch naming convention:
```
fix/<issue-number>-<brief-description>
```

Examples:
- `fix/12-add-user-authentication`
- `fix/34-search-api-pagination`

### 3. Commit

Every commit must include:
- `Closes #<issue-number>` in the commit message body
- Co-authorship footer:
  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

Example:
```
Add user authentication with Devise

Closes #12

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 4. Push & Create PR

- Push branch to origin
- Create PR using `gh pr create`
- Include `*Co-authored by Claude*` in PR body
- Always use **merge commits** (not squash)

### 5. Monitor CI

After pushing a PR, monitor CI status:

```bash
gh pr checks <pr-number> --watch
```

- **All passed**: notify user and await instruction to merge
- **Failed**: investigate the failure, propose a fix — do NOT merge

Do NOT merge the PR automatically. Wait for explicit user instruction to merge.

### 6. Merge PR

After CI passes and user gives explicit instruction:

```bash
gh pr merge <pr-number> --merge
```

### 7. Cleanup (after merge)

1. Delete the remote branch (while still in the worktree session):
   ```bash
   git push origin --delete <branch-name>
   ```

2. **Exit the worktree** using the `ExitWorktree` tool with `action: "remove"` to delete the worktree directory and local branch, then return the session to the main repository on the `main` branch.

3. **Pull latest main** to ensure the local `main` branch includes the merged changes:
   ```bash
   git pull
   ```

Do NOT delete the branch if CI failed — it may be needed for fixes.
