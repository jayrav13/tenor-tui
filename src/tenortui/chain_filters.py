"""Pure helper functions for filtering, sorting, command parsing, and visual highlighting
of options chain data in ChainTable."""

from __future__ import annotations

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
