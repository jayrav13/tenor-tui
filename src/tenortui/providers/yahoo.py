import math

import yfinance as yf

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote


def _safe_int(value, default: int = 0) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return int(value)


def _safe_float(value, default: float = 0.0) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return float(value)


class YahooProvider:
    name = "yahoo"

    def get_quote(self, symbol: str) -> Quote:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
        except Exception as e:
            raise ProviderError(f"Failed to fetch quote for {symbol}: {e}") from e

        if not info.get("regularMarketPrice"):
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found")

        return Quote(
            symbol=symbol.upper(),
            name=info.get("shortName", symbol),
            price=info["regularMarketPrice"],
            change=info.get("regularMarketChange", 0.0),
            change_percent=info.get("regularMarketChangePercent", 0.0),
            volume=info.get("regularMarketVolume", 0),
            market_cap=info.get("marketCap"),
        )

    def get_expirations(self, symbol: str) -> list[str]:
        try:
            ticker = yf.Ticker(symbol)
            return list(ticker.options)
        except Exception as e:
            raise ProviderError(f"Failed to fetch expirations for {symbol}: {e}") from e

    def get_chain(self, symbol: str, expiration: str) -> OptionsChain:
        try:
            ticker = yf.Ticker(symbol)
            chain = ticker.option_chain(expiration)
        except Exception as e:
            raise ProviderError(
                f"Failed to fetch chain for {symbol} {expiration}: {e}"
            ) from e

        return OptionsChain(
            symbol=symbol.upper(),
            expiration=expiration,
            calls=[
                self._row_to_contract(row, "call") for _, row in chain.calls.iterrows()
            ],
            puts=[
                self._row_to_contract(row, "put") for _, row in chain.puts.iterrows()
            ],
        )

    @staticmethod
    def _row_to_contract(row, option_type: str) -> OptionContract:
        return OptionContract(
            contract_symbol=row.get("contractSymbol", ""),
            option_type=option_type,
            strike=_safe_float(row.get("strike")),
            bid=_safe_float(row.get("bid")),
            ask=_safe_float(row.get("ask")),
            last_price=_safe_float(row.get("lastPrice")),
            volume=_safe_int(row.get("volume")),
            open_interest=_safe_int(row.get("openInterest")),
            implied_volatility=_safe_float(row.get("impliedVolatility")),
            delta=None,
            gamma=None,
            theta=None,
            vega=None,
            rho=None,
        )


def batch_quotes(symbols: list[str]) -> list[Quote]:
    if not symbols:
        return []
    try:
        tickers = yf.Tickers(" ".join(symbols))
    except Exception:
        return []
    quotes = []
    for symbol in symbols:
        try:
            ticker = tickers.tickers.get(symbol)
            if ticker is None:
                continue
            info = ticker.info
            if not info.get("regularMarketPrice"):
                continue
            quotes.append(
                Quote(
                    symbol=symbol,
                    name=info.get("shortName", symbol),
                    price=info["regularMarketPrice"],
                    change=info.get("regularMarketChange", 0.0),
                    change_percent=info.get("regularMarketChangePercent", 0.0),
                    volume=info.get("regularMarketVolume", 0),
                    market_cap=info.get("marketCap"),
                )
            )
        except Exception:
            continue
    return quotes
