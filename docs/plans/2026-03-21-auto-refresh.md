# Auto-refresh with Market Hours Awareness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-refresh options data during market hours (default: ON at 60s), with market state display in the status bar and ctrl+p to pause/unpause.

**Architecture:** A `market_hours.py` module provides timezone-based market state detection (no API calls needed). The app uses Textual's `set_timer` for periodic refresh, adjusting interval based on market state. Status bar shows market state and countdown to next refresh.

**Tech Stack:** Python `zoneinfo` (stdlib, no pytz needed on 3.11+), Textual timers

---

## Tasks

### Task 1: Market Hours Module
Create `src/tenortui/market_hours.py` — pure time-based US market state detection.

### Task 2: Status Bar Market State Display
Show market state and refresh countdown in status bar.

### Task 3: Auto-refresh Timer in App
Wire up periodic refresh with market-aware intervals and ctrl+p toggle.

### Task 4: Tests, Lint, PR
