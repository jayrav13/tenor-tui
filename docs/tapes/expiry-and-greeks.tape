Source docs/tapes/_common.tape
Output docs/site/docs/assets/demos/expiry-and-greeks.gif

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
Sleep 2s

# Cycle through expiries
Right
Sleep 1500ms
Right
Sleep 1500ms
Left
Sleep 1500ms

# Scroll the chain
Down
Down
Down
Down
Sleep 2s
Up
Up
Sleep 2s

Ctrl+C
Sleep 500ms
