# Git Hooks: Pre-commit and Pre-push

## Summary

Add git hooks using the `pre-commit` framework to enforce lint checks on commit and run the test suite on push. This mirrors the pattern used in the `tenor` Rails project (which uses Lefthook) but uses the Python-native `pre-commit` tool.

## Motivation

Currently there is no automated quality gate before code reaches CI. Developers can commit unlinted code and push failing tests. Adding local hooks catches these issues earlier, reducing CI churn and failed PRs.

## Design

### Framework: pre-commit

The [`pre-commit`](https://pre-commit.com/) framework manages git hooks via a YAML config file. It is Python-native, widely adopted, and already compatible with ruff via the official mirror repo.

### Hook Configuration

A `.pre-commit-config.yaml` file at the repo root defines two hook stages:

**Pre-commit (runs on every `git commit`):**
- **ruff lint** — runs `ruff check` on staged Python files
- **ruff format** — runs `ruff format --check` on staged Python files
- Both use the `astral-sh/ruff-pre-commit` mirror, pinned to a specific ruff version (matching the `>=0.4` constraint in `pyproject.toml`)

**Pre-push (runs on every `git push`):**
- **pytest** — runs `python -m pytest` as a local hook
- Configured with `always_run: true` and `pass_filenames: false` since it runs the full suite, not per-file

### Installation

Developers install hooks with:

```bash
pre-commit install && pre-commit install --hook-type pre-push
```

### Dependencies

Add `pre-commit` to the `[project.optional-dependencies] dev` list in `pyproject.toml`. No other dependencies are needed — ruff is already a dev dependency, and pre-commit downloads its own isolated copy for the hooks.

### Bypass

Standard git `--no-verify` flag skips hooks when needed (e.g., WIP commits). No custom bypass mechanism required.

### Documentation

Update CLAUDE.md to document:
- Hook installation command
- What each hook does
- How to bypass with `--no-verify`

## Files Changed

| File | Change |
|------|--------|
| `.pre-commit-config.yaml` | New — hook configuration |
| `pyproject.toml` | Add `pre-commit` to dev dependencies |
| `CLAUDE.md` | Document hook setup and usage |

## Success Criteria

- [ ] Pre-commit hook runs ruff lint and format check on staged files
- [ ] Pre-push hook runs pytest
- [ ] Hooks block on failure (non-zero exit)
- [ ] Easy to install (`pre-commit install && pre-commit install --hook-type pre-push`)
- [ ] Documented in CLAUDE.md
