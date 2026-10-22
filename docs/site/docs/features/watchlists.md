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
| <kbd>b</kbd> | Back to the watchlist panel from the chain (also `:watchlist` / `:wl`) |
| <kbd>d</kbd> | Delete the highlighted row (ticker or contract) from its list, whatever the current grouping or sort order (only while the panel is shown) |
| <kbd>S</kbd> | Sort the focused list (cycles through symbol / price / change / volume) |

Loading a ticker swaps the watchlist panel for the options chain. Press
<kbd>b</kbd> (or run `:watchlist` / `:wl`) to bring the panel back with fresh
quotes; picking a ticker from it shows the chain again. Background quote
refreshes never move focus away from the chain.

## Persistence

Watchlists are stored in `~/.config/tenor/watchlists.json`. The file is JSON,
human-readable, and safe to edit by hand if you want.

## Demo

![Add a symbol, switch lists](../assets/demos/watchlist-flow.gif){ loading=lazy }
