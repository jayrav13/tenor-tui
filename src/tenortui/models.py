from dataclasses import dataclass


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_cap: float | None


@dataclass
class OptionContract:
    contract_symbol: str
    option_type: str
    strike: float
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    rho: float | None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def has_greeks(self) -> bool:
        return self.delta is not None


@dataclass
class OptionsChain:
    symbol: str
    expiration: str
    calls: list[OptionContract]
    puts: list[OptionContract]
