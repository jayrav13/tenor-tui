Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/watchlist-flow.gif

Hide
Type "poetry run tenortui --provider fixture"
Enter
Sleep 2s
Show

Sleep 1s
Type "AAPL"
Sleep 500ms
Enter
Sleep 2s

# Tab away from search bar so app-level keys are active
Tab
Sleep 500ms

# Open watchlist picker
Type "w"
Sleep 2s

# Close picker
Escape
Sleep 1s

Ctrl+C
Sleep 500ms
