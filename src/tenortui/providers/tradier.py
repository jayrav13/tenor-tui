import requests

from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionContract, OptionsChain, Quote

PROD_URL = "https://api.tradier.com/v1"
SANDBOX_URL = "https://sandbox.tradier.com/v1"


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
            price=float(q.get("last", 0)),
            change=float(q.get("change", 0)),
            change_percent=float(q.get("change_percentage", 0)),
            volume=int(q.get("volume", 0) or 0),
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
        return OptionsChain(symbol=symbol.upper(), expiration=expiration, calls=calls, puts=puts)

    @staticmethod
    def _to_contract(opt: dict) -> OptionContract:
        greeks = opt.get("greeks") or {}
        return OptionContract(
            contract_symbol=opt.get("symbol", ""),
            option_type=opt.get("option_type", "call"),
            strike=float(opt.get("strike", 0)),
            bid=float(opt.get("bid", 0)),
            ask=float(opt.get("ask", 0)),
            last_price=float(opt.get("last", 0)),
            volume=int(opt.get("volume", 0) or 0),
            open_interest=int(opt.get("open_interest", 0) or 0),
            implied_volatility=float(opt.get("implied_volatility", 0) or 0),
            delta=greeks.get("delta"),
            gamma=greeks.get("gamma"),
            theta=greeks.get("theta"),
            vega=greeks.get("vega"),
            rho=greeks.get("rho"),
        )
