# TenorTUI Feature Roadmap Design

**Date:** 2026-03-21
**Status:** Approved

## Context

TenorTUI is a Textual-based terminal app for browsing stock options chains. It currently supports ticker search, options chain display with ATM marking, recently viewed tickers with live quotes, and two data providers (Yahoo Finance and Tradier). This design defines 10 core features and 5 bonus features to transform it into a comprehensive, keyboard-driven stock market TUI.

TenorTUI is used alongside [tenor](https://github.com/jayrav13/tenor), an AI-driven trading platform with a CSP screener (`/stonks`). However, TenorTUI must remain fully agnostic — no database dependencies, purely API-driven.

## Design Decisions

### Yahoo as Foundation Data Layer
Yahoo Finance is the base data layer — always available, free, no auth required, and provides the broadest data surface (quotes, options, fundamentals, news, historical prices). Tradier and future providers serve as **enhancement layers** that overlay Greeks, streaming data, or broker-specific features on top.

The `DataProvider` protocol stays focused on options chain data. New features (news, fundamentals, charts) call Yahoo utilities directly, similar to how `batch_quotes()` already works.

### No Broker Account Integration
TenorTUI is purely a market data scanner. Portfolio management, positions, orders, and trading stay in tenor.

### No CSP Screener
The CSP screener requires database access. TenorTUI provides rich options data (Greeks, IV, volume, OI) for manual scanning. CSP logic stays in tenor.

### Keyboard-First, Vim-Inspired UX
Every feature is designed around keyboard navigation with vim-style bindings. A discoverable help overlay (`?`) and command palette (`:`) make the app learnable.

## Features

### Foundation (Do First)

#### 1. Vim-style Keyboard Navigation + Help Overlay (GH #1)
- Global: `j/k` up/down, `h/l` left/right panes, `g/G` top/bottom, number keys for panes
- `?` toggles context-aware help overlay, `:` opens command palette
- Status bar shows `? for help` hint

#### 2. Settings Panel (GH #4)
- Toggle with `,` or `:settings`
- Auto-refresh (on/off, interval), provider, display toggles, Tradier config
- Persists to `~/.config/tenor/config.yaml`, takes effect immediately

#### 3. Auto-refresh with Market Hours Awareness (GH #7)
- Default: ON at 60s during market hours
- Market clock in status bar (session type + countdown)
- Smart refresh: slower/stopped outside market hours
- `ctrl+p` to pause/unpause

### Market Data Enrichment

#### 4. Stock Fundamentals Panel (GH #11)
- Compact mode (default): inline metrics row — P/E, EPS, dividends, earnings date, 50/200-day MAs
- Expanded mode (`f`): full panel with 52-week range, volume vs avg, sector, MA context
- Always Yahoo, regardless of provider

#### 5. News Panel (GH #13)
- Toggle with `N`, vim-nav with `j/k`, open in browser with `o`
- Yahoo Finance news API (ported from tenor's Ruby client)
- 1-minute cache, auto-fetch on ticker load
- `News (5)` count in status bar

#### 6. Watchlists (GH #5)
- Multiple named watchlists replacing RecentlyViewed
- Persist to `~/.config/tenor/watchlists.json`
- `w` to add, `W` to manage, `d` to remove
- Live quotes via `batch_quotes()`, sortable

### Visualization

#### 7. Price Charts (GH #8)
- `plotext` or Textual canvas for terminal rendering
- Intraday (1m/5m bars) and historical (1D-5Y) views
- Candlestick/line with 50/200-day MA overlays
- `c` to toggle, `[`/`]` to cycle timeframes

#### 8. Options Visualizations (GH #10)
- IV smile/skew across strikes with ATM marker
- OI distribution (calls vs puts bar chart)
- Volume heatmap with color intensity
- `v` to toggle, `1/2/3` to switch visualization type
- No additional API calls — uses cached chain data

### Enhanced Options Data

#### 9. Enhanced Chain Table (GH #14)
- Sortable columns with direction indicators
- Filtering: zero-volume, ITM/OTM, delta range, min volume/OI
- IV color-coding, high-volume highlights, earnings warnings
- Improved Greeks formatting with delta gradient

#### 10. Multi-expiry Comparison View (GH #15)
- `m` to open, compares same strike across expirations
- Columns: DTE, premium, IV, delta, theta, annualized return
- Pre-fetches up to 6 nearest expirations in background

## Bonus Features

#### 11. Market Hours Countdown / Session Timer (GH #2)
Status bar enhancement showing time to open/close and current session type.

#### 12. Watchlist Alerts / Threshold Highlighting (GH #3)
Per-watchlist configurable thresholds (change %, IV rank, volume spikes) with visual indicators.

#### 13. Volume Sub-chart for Price Charts (GH #6)
Volume bars below price chart, color-coded by direction. Depends on #8.

#### 14. Client-side Greeks Calculation (GH #9)
Black-Scholes approximation when provider doesn't supply Greeks. Off by default, visual indicator for calculated values.

#### 15. Bid-Ask Spread Quality Indicator (GH #12)
Color-coded spread quality per contract row (tight/moderate/wide as % of mid). Configurable thresholds.

## Keybinding Summary

| Key | Action |
|-----|--------|
| `j/k` | Up/down in lists/tables |
| `h/l` | Left/right between panes |
| `g/G` | Top/bottom of list |
| `1-5` | Switch panes |
| `tab` | Next pane |
| `/`, `s` | Focus search |
| `?` | Help overlay |
| `:` | Command palette |
| `r` | Manual refresh |
| `ctrl+p` | Pause/unpause auto-refresh |
| `q` | Quit |
| `f` | Toggle fundamentals |
| `N` | Toggle news |
| `c` | Toggle charts |
| `v` | Toggle options visualizations |
| `m` | Multi-expiry comparison |
| `w` | Add to watchlist |
| `W` | Watchlist manager |
| `,` | Settings |
| `o` | Open in browser |

## Implementation Priority

1. **Foundation** (#1, #4, #7) — keyboard nav, settings, auto-refresh
2. **Market Data** (#11, #13, #5) — fundamentals, news, watchlists
3. **Enhanced Options** (#14, #15) — chain table improvements, multi-expiry
4. **Visualization** (#8, #10) — price charts, options viz
5. **Bonus** (#2, #3, #6, #9, #12) — as time permits
