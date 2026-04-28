Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/launch-and-search.gif

# Use --provider fixture: deterministic offline data, no API keys, no network.
# Required for reproducible recordings. If you change this, regenerate all demo
# GIFs together (`make demos`) so they stay consistent.
Hide
Type "poetry run tenortui --provider fixture"
Enter
Sleep 2s
Show

Sleep 1s
Type "AAPL"
Sleep 500ms
Enter
Sleep 3s

# Switch expiry tab
Right
Sleep 1500ms
Right
Sleep 1500ms
Left
Sleep 1500ms

# Quit
Ctrl+C
Sleep 500ms
