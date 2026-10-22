# Watchlists

Watchlists group symbols you care about. They replaced the older "Recently
Viewed" panel — you can have multiple named watchlists, each containing
equity tickers and (optionally) specific options contracts.

Watchlists change only when you ask them to. Searching for or selecting a
ticker loads it without touching any list; press <kbd>w</kbd> to add the
current symbol (or the highlighted contract) to a list.

![Watchlist picker](../assets/snapshots/watchlist-modal.svg){ loading=lazy }

## Keybindings

| Key | Action |
|---|---|
| <kbd>w</kbd> | Open the watchlist picker (add current symbol to a list) |
| <kbd>W</kbd> | Open the watchlist manager (create / rename / delete lists) |
| <kbd>d</kbd> | Delete the focused symbol from its list |
| <kbd>S</kbd> | Sort the focused list (cycles through symbol / price / change / volume) |

## Persistence

Watchlists are stored in `~/.config/tenor/watchlists.json`. The file is JSON,
human-readable, and safe to edit by hand if you want.

## Demo

![Add a symbol, switch lists](../assets/demos/watchlist-flow.gif){ loading=lazy }
