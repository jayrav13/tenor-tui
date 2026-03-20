from typing import Protocol

from tenortui.models import Quote, OptionsChain


class DataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> Quote: ...
    def get_expirations(self, symbol: str) -> list[str]: ...
    def get_chain(self, symbol: str, expiration: str) -> OptionsChain: ...
