from tenortui.providers.base import DataProvider as DataProvider
from tenortui.providers.fixture import FixtureProvider
from tenortui.providers.tradier import TradierProvider
from tenortui.providers.yahoo import YahooProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
    "tradier": TradierProvider,
    "fixture": FixtureProvider,
}
