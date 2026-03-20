import pytest

from tenortui.app import TenorTUI


@pytest.fixture
def app(fake_provider):
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_app_launches(app):
    async with app.run_test() as pilot:
        assert app.title == "TenorTUI"


@pytest.mark.asyncio
async def test_search_ticker(app):
    async with app.run_test() as pilot:
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
