# Plan: keep the active watchlist when deleting a list before it (#57)

## Approach

`delete_watchlist()` in `src/tenortui/watchlists.py` only clamps
`active_index` when it runs past the end. After popping `index`, decrement
`active_index` when `index < active_index`; keep the clamp for deleting the
active (or last) list. Treat an out-of-range `index` as a no-op.

## Files

- `src/tenortui/watchlists.py`: fix `delete_watchlist`.
- `tests/test_watchlists.py`: new tests.
- `CHANGELOG.md`: `### Fixed` entry under `[Unreleased]`.

## Tests

- Deleting a list before the active one keeps the same list active.
- Deleting a list after the active one leaves `active_index` unchanged.
- Deleting the active list (not last) yields a valid index.
- Out-of-range `index` is a no-op.

## Out of scope

UI changes to the Watchlist Manager; no docs-site change (behavior now
matches what users already expect).
