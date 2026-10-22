# Plan: reshow the watchlist panel (#66)

## Problem

After the first ticker load the watchlist panel is hidden and nothing brings
it back. Every watchlist quote refresh (including each auto-refresh cycle)
also focuses the hidden panel's `ListView`, so a later `d` silently deletes a
saved watchlist entry.

## Approach

All changes are in `src/tenortui/app.py` plus the help overlay.

1. `action_show_watchlist`: show `WatchlistPanel`, hide `ChainTable`, rebuild
   the list, refresh quotes and focus the list. Bound to `b` in `on_key` and
   to the `:watchlist` / `:wl` palette commands.
2. `_fetch_watchlist_quotes(focus=False)`: focus the `ListView` only when
   `focus=True` **and** `panel.display`. Mount, tab switch, manager close and
   explicit show pass `focus=True`; auto-refresh does not.
3. `_action_remove_from_watchlist`: return early when the panel is not
   displayed.
4. Add a `b` row to the help overlay and the keybindings / watchlists docs.

## Deviations

- The show action calls `panel._rebuild_list()` instead of
  `set_watchlists(...)`. `set_watchlists` rebuilds the tabs with
  `remove_children()` and immediately mounts buttons with the same
  `wl-tab-<i>` ids, which raises DuplicateIds asynchronously and hung the
  Pilot (`WaitForScreenTimeout`). The panel shares the app's `WatchlistData`,
  so rebuilding the list picks up item changes; tabs only change through the
  manager, which already calls `set_watchlists`.
- Review follow-up (PR #76): `action_show_watchlist` focuses the `ListView`
  synchronously instead of relying only on the `focus=True` worker, because
  an auto-refresh in the same exclusive worker group can cancel that worker
  before it focuses. `_load_ticker` now calls `_focus_first_table()` only
  while the chain is displayed, so a load that finishes after `b` does not
  focus the hidden chain.

## Tests

`tests/test_watchlist_reshow.py`: `b` / `:watchlist` / `:wl` show the panel,
quotes refresh on show, empty-at-launch case, selecting from the reshown
panel shows the chain, background refresh keeps chain focus, hidden `d` is a
no-op, help overlay lists `b`, focus survives a cancelled fetch, and a ticker
load finishing after `b` keeps focus on the list.
