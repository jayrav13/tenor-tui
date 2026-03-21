import requests

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote

PROD_URL = "https://api.tradier.com/v1"
SANDBOX_URL = "https://sandbox.tradier.com/v1"


def _safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _safe_int(value, default: int = 0) -> int:
    if value is None:
        return default
    return int(value)


class TradierProvider:
    name = "tradier"

    def __init__(self, api_key: str, sandbox: bool = False):
        self._api_key = api_key
        self._base_url = SANDBOX_URL if sandbox else PROD_URL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            resp = requests.get(
                f"{self._base_url}{path}",
                headers=self._headers(),
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise ProviderError(f"Tradier API error: {e}") from e

    def get_quote(self, symbol: str) -> Quote:
        data = self._get("/markets/quotes", params={"symbols": symbol})
        quotes = data.get("quotes", {})
        if "unmatched_symbols" in quotes:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found")
        q = quotes.get("quote", {})
        return Quote(
            symbol=q["symbol"],
            name=q.get("description", symbol),
            price=_safe_float(q.get("last")),
            change=_safe_float(q.get("change")),
            change_percent=_safe_float(q.get("change_percentage")),
            volume=_safe_int(q.get("volume")),
            market_cap=q.get("market_cap"),
        )

    def get_expirations(self, symbol: str) -> list[str]:
        data = self._get("/markets/options/expirations", params={"symbol": symbol})
        dates = data.get("expirations", {}).get("date", [])
        return dates if isinstance(dates, list) else [dates]

    def get_chain(self, symbol: str, expiration: str) -> OptionsChain:
        data = self._get(
            "/markets/options/chains",
            params={"symbol": symbol, "expiration": expiration, "greeks": "true"},
        )
        options = data.get("options", {}).get("option", [])
        calls = []
        puts = []
        for opt in options:
            contract = self._to_contract(opt)
            if contract.option_type == "call":
                calls.append(contract)
            else:
                puts.append(contract)
        return OptionsChain(
            symbol=symbol.upper(), expiration=expiration, calls=calls, puts=puts
        )

    @staticmethod
    def _to_contract(opt: dict) -> OptionContract:
        greeks = opt.get("greeks") or {}
        return OptionContract(
            contract_symbol=opt.get("symbol", ""),
            option_type=opt.get("option_type", "call"),
            strike=_safe_float(opt.get("strike")),
            bid=_safe_float(opt.get("bid")),
            ask=_safe_float(opt.get("ask")),
            last_price=_safe_float(opt.get("last")),
            volume=_safe_int(opt.get("volume")),
            open_interest=_safe_int(opt.get("open_interest")),
            implied_volatility=_safe_float(opt.get("implied_volatility")),
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            theta=greeks.get("theta"),
            vega=greeks.get("vega"),
            rho=greeks.get("rho"),
        )
