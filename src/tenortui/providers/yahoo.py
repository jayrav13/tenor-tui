import datetime
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


def _safe_float_or_none(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _format_earnings_date(timestamp) -> str | None:
    if timestamp is None:
        return None
    try:
        dt = datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc)
        return dt.strftime("%b %d")
    except (ValueError, TypeError, OSError):
        return None


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
            pe_ratio=_safe_float_or_none(info.get("trailingPE")),
            eps=_safe_float_or_none(info.get("trailingEps")),
            dividend_yield=_safe_float_or_none(info.get("dividendYield")),
            earnings_date=_format_earnings_date(info.get("earningsTimestamp")),
            moving_avg_50d=_safe_float_or_none(info.get("fiftyDayAverage")),
            moving_avg_200d=_safe_float_or_none(info.get("twoHundredDayAverage")),
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


def fetch_fundamentals(quote: Quote) -> Quote:
    """Enrich a Quote with fundamental data from Yahoo Finance.

    Always uses Yahoo regardless of which provider supplied the quote.
    Returns the same quote with fundamental fields populated.
    """
    try:
        ticker = yf.Ticker(quote.symbol)
        info = ticker.info
    except Exception:
        return quote

    quote.pe_ratio = _safe_float_or_none(info.get("trailingPE"))
    quote.eps = _safe_float_or_none(info.get("trailingEps"))
    quote.dividend_yield = _safe_float_or_none(info.get("dividendYield"))
    quote.earnings_date = _format_earnings_date(info.get("earningsTimestamp"))
    quote.moving_avg_50d = _safe_float_or_none(info.get("fiftyDayAverage"))
    quote.moving_avg_200d = _safe_float_or_none(info.get("twoHundredDayAverage"))
    return quote


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
