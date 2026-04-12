# Watchlists Implementation Progress

**Issue:** #5
**Branch:** `worktree-fix-5-watchlists`
**Worktree:** `.claude/worktrees/fix-5-watchlists`
**Plan:** `docs/plans/2026-04-04-watchlists.md`
**Spec:** `docs/specs/2026-04-04-watchlists-design.md`

## Execution Method

Using **subagent-driven development** — dispatch a fresh subagent per task with two-stage review (spec then quality) after each.

## Task Status

| Task | Description | Status |
|------|-------------|--------|
| 1 | Watchlist data models and persistence (`watchlists.py`, `test_watchlists.py`) | DONE - reviewed + hardened, 14 tests passing (commits e218467, 8cc25f8) |
| 2 | Watchlist CRUD operations (add/remove/create/rename/delete) | DONE - included in Task 1 implementation |
| 3 | History migration (`migrate_from_history`) | DONE - included in Task 1 implementation |
| 4 | WatchlistPanel widget | DONE - commit d97b5d7, 6 tests |
| 5 | WatchlistPicker and WatchlistManager modals | DONE - commit 02ce2d6, 2 tests |
| 6 | Integrate WatchlistPanel into app (replace RecentlyViewed) | DONE - commit c00860b, updated 6 test files |
| 7 | Add w/W/d keybindings for watchlist actions | DONE - commit de9d777, 13 keybinding tests |
| 8 | Integration tests | DONE - commit 569b220, 5 integration tests |
| 9 | Sorting support (symbol/price/change/volume) | DONE - commit d2c4dc9, 5 sorting tests |
| 10 | Cleanup and lint | DONE - all clean, no changes needed |

## Summary

All 10 tasks complete. 381 tests passing (up from 353 baseline). Lint and format clean.

### Commits on branch (main..HEAD):
- fefe547 feat: add watchlist data models and persistence
- 6baf988 fix: harden watchlist persistence per code review
- 4b2a2ba docs: add watchlists spec, plan, and progress tracker
- 9deb8d3 docs: mark Task 1 reviewed in watchlists progress tracker
- d97b5d7 feat: add WatchlistPanel widget with grouped display
- 02ce2d6 feat: add WatchlistPicker and WatchlistManager modals
- c00860b feat: integrate WatchlistPanel into app, replacing RecentlyViewed
- de9d777 feat: add w/W/d keybindings for watchlist management
- 569b220 test: add watchlist integration tests
- d2c4dc9 feat: add watchlist sorting by symbol/price/change/volume

### Known Issues:
- `set_watchlists` / `_rebuild_tabs` can trigger a Textual `DuplicateIds` error when called while panel is mounted (Textual defers `remove_children()` DOM removal). Wrapped in try/except at call sites. The panel still renders correctly since `_watchlist_data` is mutated in-place.
