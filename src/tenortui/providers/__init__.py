from tenortui.providers.base import DataProvider
from tenortui.providers.yahoo import YahooProvider

PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
}
