"""Pure helper functions for filtering, sorting, command parsing, and visual highlighting
of options chain data in ChainTable."""

from __future__ import annotations

import re
from dataclasses import dataclass

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
