from tenortui.providers.base import DataProvider
from tenortui.providers.yahoo import YahooProvider
from tenortui.providers.tradier import TradierProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
    "tradier": TradierProvider,
}
