"""Pure helper functions for filtering, sorting, command parsing, and visual highlighting
of options chain data in ChainTable."""

from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import median
from typing import Sequence

from tenortui.models import OptionContract


# ---------------------------------------------------------------------------
# ChainFilters dataclass
# ---------------------------------------------------------------------------


@dataclass
class ChainFilters:
    """Immutable-ish container for all active chain filters."""

    min_volume: int | None = None
    min_oi: int | None = None
    min_delta: float | None = None
    max_delta: float | None = None
    moneyness: str | None = None  # "itm" | "otm" | None

    @property
    def is_active(self) -> bool:
        """Return True if any filter is set."""
        return any(
            v is not None
            for v in (
                self.min_volume,
                self.min_oi,
                self.min_delta,
                self.max_delta,
                self.moneyness,
            )
        )

    @property
    def active_count(self) -> int:
        """Return the number of active filters."""
        return sum(
            1
            for v in (
                self.min_volume,
                self.min_oi,
                self.min_delta,
                self.max_delta,
                self.moneyness,
            )
            if v is not None
        )


# ---------------------------------------------------------------------------
# Task 1: Filtering
# ---------------------------------------------------------------------------


def filter_contracts(
    contracts: list[OptionContract],
    filters: ChainFilters,
    current_price: float | None = None,
    side: str | None = None,
) -> list[OptionContract]:
    """Apply all active filters to *contracts* and return the subset that passes."""
    if not filters.is_active:
        return contracts

    result: list[OptionContract] = []
    for c in contracts:
        # Volume filter
        if filters.min_volume is not None and c.volume < filters.min_volume:
            continue

        # Open-interest filter
        if filters.min_oi is not None and c.open_interest < filters.min_oi:
            continue

        # Delta filter (uses absolute value; contracts with None delta are excluded)
        if filters.min_delta is not None or filters.max_delta is not None:
            if c.delta is None:
                continue
            abs_delta = abs(c.delta)
            if filters.min_delta is not None and abs_delta < filters.min_delta:
                continue
            if filters.max_delta is not None and abs_delta > filters.max_delta:
                continue

        # Moneyness filter
        if (
            filters.moneyness is not None
            and current_price is not None
            and side is not None
        ):
            if side == "call":
                if filters.moneyness == "itm" and not c.strike < current_price:
                    continue
                if filters.moneyness == "otm" and not c.strike > current_price:
                    continue
            elif side == "put":
                if filters.moneyness == "itm" and not c.strike > current_price:
                    continue
                if filters.moneyness == "otm" and not c.strike < current_price:
                    continue

        result.append(c)

    return result


# ---------------------------------------------------------------------------
# Task 2: Sorting
# ---------------------------------------------------------------------------

# Maps user-visible column names → attribute names on OptionContract (or special keys).
SORT_KEYS: dict[str, str] = {
    "strike": "strike",
    "bid": "bid",
    "ask": "ask",
    "spread": "spread_percent",
    "mid": "mid",
    "last": "last_price",
    "vol": "volume",
    "oi": "open_interest",
    "iv": "implied_volatility",
    "delta": "delta",
    "gamma": "gamma",
    "theta": "theta",
    "vega": "vega",
    "rho": "rho",
}


def sort_contracts(
    contracts: list[OptionContract],
    column: str | None,
    reverse: bool = False,
) -> list[OptionContract]:
    """Sort *contracts* by *column*.  None values sort to the end.
    If *column* is None or not recognised, fall back to strike sort."""
    attr = SORT_KEYS.get(column or "", "strike") if column is not None else "strike"

    def _key(c: OptionContract):
        val = getattr(c, attr, None)
        # For properties like mid/spread_percent the attribute always exists,
        # but for optional Greek columns val can be None.
        if val is None:
            return (1, 0)  # sort None to end
        return (0, val)

    return sorted(contracts, key=_key, reverse=reverse)


# ---------------------------------------------------------------------------
# Task 3: Command Parsing
# ---------------------------------------------------------------------------


def parse_filter_command(command: str) -> ChainFilters | None:
    """Parse a human-typed filter command into a ``ChainFilters`` instance.

    Supported formats:
    - ``volume > N``  /  ``vol > N``  → min_volume = N+1
    - ``oi > N``                      → min_oi = N+1
    - ``itm``  /  ``otm``             → moneyness
    - ``delta <min> <max>``           → min_delta, max_delta
    - ``clear``                       → returns None (clear all filters)
    - anything else                   → returns None
    """
    if not command or not command.strip():
        return None

    cmd = command.strip().lower()

    # Clear
    if cmd == "clear":
        return None

    # Moneyness
    if cmd == "itm":
        return ChainFilters(moneyness="itm")
    if cmd == "otm":
        return ChainFilters(moneyness="otm")

    # volume / vol > N
    m = re.fullmatch(r"(?:volume|vol)\s*>\s*(\d+)", cmd)
    if m:
        threshold = int(m.group(1))
        return ChainFilters(min_volume=threshold + 1)

    # oi > N
    m = re.fullmatch(r"oi\s*>\s*(\d+)", cmd)
    if m:
        threshold = int(m.group(1))
        return ChainFilters(min_oi=threshold + 1)

    # delta <min> <max>
    m = re.fullmatch(r"delta\s+([\d.]+)\s+([\d.]+)", cmd)
    if m:
        return ChainFilters(min_delta=float(m.group(1)), max_delta=float(m.group(2)))

    return None


# ---------------------------------------------------------------------------
# Task 4: Visual Highlighting Helpers
# ---------------------------------------------------------------------------


def iv_percentile_rank(iv: float, all_ivs: list[float]) -> float:
    """Return the percentile rank (0.0-1.0) of *iv* within *all_ivs*.

    Returns 0.0 for empty or single-element lists.
    """
    if len(all_ivs) <= 1:
        return 0.0
    min_iv = min(all_ivs)
    max_iv = max(all_ivs)
    if max_iv == min_iv:
        return 0.0
    return (iv - min_iv) / (max_iv - min_iv)


def compute_chain_median(values: Sequence[float]) -> float:
    """Return the median of *values*, or 0.0 for an empty sequence."""
    if not values:
        return 0.0
    return median(values)


def is_high_activity(value: float, median_value: float) -> bool:
    """Return True if *value* is strictly greater than twice *median_value*."""
    return value > 2 * median_value


def delta_color(delta: float | None) -> str:
    """Return a Textual-compatible color name based on absolute delta magnitude.

    - abs(delta) >= 0.7 -> "green"  (deep in the money)
    - abs(delta) >= 0.3 -> "yellow" (near the money)
    - otherwise         -> "red"    (far out of the money)
    - None              -> ""
    """
    if delta is None:
        return ""
    abs_d = abs(delta)
    if abs_d >= 0.7:
        return "green"
    if abs_d >= 0.3:
        return "yellow"
    return "red"


def iv_color(percentile: float) -> str:
    """Return a Textual-compatible color name based on IV percentile rank.

    - <= 0.25 -> "cyan"        (very low IV)
    - <= 0.50 -> "yellow"      (below-average IV)
    - <= 0.75 -> "dark_orange" (above-average IV)
    - >  0.75 -> "red"         (very high IV)
    """
    if percentile <= 0.25:
        return "cyan"
    if percentile <= 0.50:
        return "yellow"
    if percentile <= 0.75:
        return "dark_orange"
    return "red"
