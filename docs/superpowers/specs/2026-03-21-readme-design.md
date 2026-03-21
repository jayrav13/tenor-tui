# README Redesign — Design Spec

**Issue:** #16
**Date:** 2026-03-21
**Status:** Draft

## Goal

Replace the minimal README with a comprehensive one that serves two audiences:
1. **Users** who want to install and use TenorTUI
2. **Developers** who want to understand the architecture and contribute

The README should communicate TenorTUI's two key differentiators:
- **Data-source agnostic** — a terminal client for *your* data provider, with a UI that flexes based on what the provider offers (e.g., Greeks appear when available)
- **Vim-native navigation** — first-class vim keybindings throughout

It should also highlight that TenorTUI is a **Claude-first project** with structured workflows that make it easy for multiple contributors (human or AI) to work in parallel.

## Structure

### 1. Header & Tagline
- Project name + one-line description
- Brief (2-3 sentence) pitch: data-source agnostic options chain viewer with vim-native navigation, built for the terminal

### 2. Features
- 3-4 bullet points, concise:
  - Pluggable data providers (Yahoo Finance out of the box, Tradier with Greeks)
  - Vim-style navigation (j/k/g/G/h/l) + command palette
  - Auto-detection of ATM strike with viewport centering
  - Recently viewed tickers with live quotes

### 3. Quick Start
- Prerequisites: Python 3.11+, git
- Clone + install + run in 3 commands
- Note that Yahoo Finance works with zero configuration

### 4. Configuration
- Config file location (`~/.config/tenor/config.yaml`, legacy `~/.tenorrc` fallback)
- Full example config with comments explaining each field
- Provider-specific setup:
  - **Yahoo Finance**: no config needed, explain what it provides (quotes, chains, no Greeks)
  - **Tradier**: API key required, sandbox mode option, explain what it adds (Greeks)
- CLI override: `--provider` flag

### 5. Keybindings
- Three subsections matching the help overlay:
  - **Navigation**: j/k, h/l, g/G, Tab/Shift+Tab
  - **Actions**: / or s (search), r (refresh), Enter (select), q (quit)
  - **Panels**: ? (help), : (command palette)
- Command palette commands: `:quit`, `:search <SYMBOL>`, `:help`

### 6. Data Providers
- Comparison table: Provider | Auth Required | Greeks | Source
- Brief explanation of the provider protocol for people interested in adding their own
- Point to `providers/base.py` as the interface to implement

### 7. Development
- Setup: venv creation, `pip install -e ".[dev]"`
- Commands: pytest, ruff check, ruff format
- Brief architecture overview:
  - App flow (launch → history → ticker → expirations → chain)
  - Widget hierarchy (TickerBar, RecentlyViewed, ExpirySelector, ChainTable, StatusBar, CommandPalette)
  - Provider pattern (sync methods wrapped with `asyncio.to_thread`)
  - Config + history file locations
- Pointer to CLAUDE.md for full development reference

### 8. Built with Claude
- TenorTUI is developed Claude-first using Claude Code
- Parallel development via git worktrees — multiple features developed simultaneously
- Structured workflow: GitHub Issues → worktree branch → PR → merge
- CLAUDE.md is the canonical development guide
- Contributions welcome — both human and AI-assisted

## Content Guidelines

- **Tone**: Friendly but not wordy. Respect the reader's time.
- **Code blocks**: Use them liberally for commands and config examples.
- **Tables**: Use for keybindings and provider comparison — scannable at a glance.
- **Length**: Aim for a README that fits in ~150-200 lines. Comprehensive but not sprawling.
- **No emojis** unless the user requests them later.

## Out of Scope

- Screenshots/terminal recordings (issue mentions "if available" — we don't have them)
- Badges (can add later)
- Detailed API documentation for providers (that belongs in code docs)

## Success Criteria (from Issue #16)

- [ ] README covers installation from Git repo
- [ ] README covers pip install (editable and standard)
- [ ] README documents config file format with examples
- [ ] README explains Yahoo vs Tradier provider setup
- [ ] README includes basic usage and key bindings
- [ ] README is clear enough for a first-time user to get started
