# Plan: offline, isolated fixture provider (#62)

Issue: #62

## Approach

Treat the fixture provider as an offline, ephemeral demo mode, driven by a
provider attribute rather than a name check:

1. `providers/fixture.py`: add `offline = True` to `FixtureProvider`.
2. `app.py`:
   - `self._offline = getattr(provider, "offline", False)` in `__init__`;
   - when offline, start from a fresh in-memory default `WatchlistData`
     instead of `migrate_from_history()`;
   - route every `save_watchlists(...)` call through a `_save_watchlists()`
     helper that is a no-op when offline;
   - skip `fetch_fundamentals` in `_load_ticker` when offline (the fixture
     quote already carries frozen fundamentals);
   - in `_fetch_watchlist_quotes`, fetch equity quotes with
     `self._provider.get_quote` when offline instead of Yahoo `batch_quotes`.
3. `bin/snapshot`: a comment noting isolation comes from the provider; no
   behavior change. Tapes need no change.
4. Docs: Fixture section of `docs/site/docs/features/providers.md`;
   CHANGELOG `[Unreleased]` Fixed entry. Regenerate snapshots from the
   isolated mode.

## Files

- `src/tenortui/providers/fixture.py`, `src/tenortui/app.py`, `bin/snapshot`
- `tests/test_offline_fixture.py` (new)
- `docs/site/docs/features/providers.md`, `CHANGELOG.md`, snapshot SVGs

## Tests

- fixture provider exposes `offline = True`
- `_load_ticker` under the fixture provider never calls `fetch_fundamentals`
  and shows the frozen P/E
- under the fixture provider the app neither reads nor writes the watchlist
  file (default paths redirected to `tmp_path`); edits stay in memory
- `bin/snapshot` watchlist-modal SVG does not contain a private watchlist name
- watchlist equity prices come from the provider, not `batch_quotes`
- a non-offline provider (`FakeProvider`) still fetches fundamentals and
  persists watchlists

## Out of scope

- The FRED risk-free-rate fetch (only runs when a FRED key is configured).
- Changes to VHS tapes or `make demos` beyond regenerating assets.
