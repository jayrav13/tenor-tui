import yfinance as yf

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote


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
            raise ProviderError(f"Failed to fetch chain for {symbol} {expiration}: {e}") from e

        return OptionsChain(
            symbol=symbol.upper(),
            expiration=expiration,
            calls=[self._row_to_contract(row, "call") for _, row in chain.calls.iterrows()],
            puts=[self._row_to_contract(row, "put") for _, row in chain.puts.iterrows()],
        )

    @staticmethod
    def _row_to_contract(row, option_type: str) -> OptionContract:
        return OptionContract(
            contract_symbol=row.get("contractSymbol", ""),
            option_type=option_type,
            strike=float(row.get("strike", 0)),
            bid=float(row.get("bid", 0)),
            ask=float(row.get("ask", 0)),
            last_price=float(row.get("lastPrice", 0)),
            volume=int(row.get("volume", 0) or 0),
            open_interest=int(row.get("openInterest", 0) or 0),
            implied_volatility=float(row.get("impliedVolatility", 0)),
            delta=None, gamma=None, theta=None, vega=None, rho=None,
        )
