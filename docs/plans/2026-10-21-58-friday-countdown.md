# Plan: Friday-evening countdown to Monday pre-market (#58)

Issue: #58

## Approach

In `time_to_next_state()` (`src/tenortui/market_hours.py`), the CLOSED
branch for "after 8 PM" always adds one day, so Friday evening counts down to
Saturday 04:00. Make it skip to the next weekday: add 3 days on Friday
(Friday -> Monday) and 1 day otherwise. The arithmetic stays in wall-clock
minutes, like the existing weekend branch.

## Files

- `src/tenortui/market_hours.py`
- `tests/test_market_hours.py`
- `CHANGELOG.md`
- this plan

## Tests

Regression tests in `TestTimeToNextState`:

- Friday 20:00 and Friday 23:59 ET count down to Monday 04:00
- Friday 21:00 ET counts down 55 h (the issue's reproduction)
- Thursday 21:00 ET still counts down to Friday 04:00
- Friday after-hours (18:00) still counts down to 20:00

## Docs

No user-facing doc surface shows this countdown (the status bar shows plain
"Market Closed"), so only `CHANGELOG.md` changes.

## Out of scope

Market holidays, DST-transition precision, and showing a countdown in the
CLOSED state.
