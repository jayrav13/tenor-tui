import pytest

from tenortui.app import TenorTUI
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.chain_table import ChainTable


@pytest.fixture
def app(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_app_launches(app):
    async with app.run_test():
        assert app.title == "TenorTUI"


@pytest.mark.asyncio
async def test_search_ticker(app):
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        from tenortui.widgets.ticker_bar import TickerBar

        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered or "213.25" in rendered


@pytest.mark.asyncio
async def test_focus_search(app):
    async with app.run_test() as pilot:
        await pilot.press("slash")
        from tenortui.widgets.ticker_bar import TickerBar

        input_widget = app.query_one(TickerBar).query_one("#ticker-input")
        assert input_widget.has_focus


@pytest.mark.asyncio
async def test_recently_viewed_hidden_when_no_history(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test():
        rv = test_app.query_one(RecentlyViewed)
        assert rv.display is False


@pytest.mark.asyncio
async def test_recently_viewed_shown_when_history_exists(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: ["AAPL", "MSFT"])
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test():
        rv = test_app.query_one(RecentlyViewed)
        ct = test_app.query_one(ChainTable)
        assert rv.display is True
        assert ct.display is False


@pytest.mark.asyncio
async def test_recently_viewed_hidden_after_ticker_load(fake_provider, monkeypatch):
    monkeypatch.setattr("tenortui.app.load_history", lambda: ["AAPL"])
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: ["AAPL"])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test() as pilot:
        test_app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await test_app.workers.wait_for_complete()
        rv = test_app.query_one(RecentlyViewed)
        assert rv.display is False
