import pytest
from unittest.mock import patch, MagicMock

import tenortui.risk_free_rate as rfr_module
from tenortui.risk_free_rate import get_risk_free_rate


@pytest.fixture(autouse=True)
def reset_cache():
    rfr_module._cached_rate = None
    rfr_module._cached_is_live = False
    yield


def _mock_response(observations):
    resp = MagicMock()
    resp.json.return_value = {"observations": observations}
    resp.raise_for_status = MagicMock()
    return resp


class TestGetRiskFreeRate:
    def test_successful_fetch(self):
        resp = _mock_response([{"date": "2026-03-20", "value": "4.32"}])
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate()
        assert rate == pytest.approx(0.0432)
        assert is_live is True

    def test_skips_missing_data(self):
        resp = _mock_response(
            [
                {"date": "2026-03-20", "value": "."},
                {"date": "2026-03-19", "value": "4.30"},
            ]
        )
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate()
        assert rate == pytest.approx(0.0430)
        assert is_live is True

    def test_api_failure_returns_fallback(self):
        with patch(
            "tenortui.risk_free_rate.requests.get", side_effect=Exception("timeout")
        ):
            rate, is_live = get_risk_free_rate(fallback=0.05)
        assert rate == 0.05
        assert is_live is False

    def test_caching(self):
        resp = _mock_response([{"date": "2026-03-20", "value": "4.32"}])
        with patch(
            "tenortui.risk_free_rate.requests.get", return_value=resp
        ) as mock_get:
            get_risk_free_rate()
            get_risk_free_rate()
            assert mock_get.call_count == 1

    def test_empty_observations_returns_fallback(self):
        resp = _mock_response([])
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate(fallback=0.03)
        assert rate == 0.03
        assert is_live is False

    def test_all_missing_data_returns_fallback(self):
        resp = _mock_response(
            [
                {"date": "2026-03-20", "value": "."},
                {"date": "2026-03-19", "value": "."},
            ]
        )
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate(fallback=0.05)
        assert rate == 0.05
        assert is_live is False

    def test_rate_conversion(self):
        resp = _mock_response([{"date": "2026-03-20", "value": "5.00"}])
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate()
        assert rate == pytest.approx(0.05)

    def test_custom_fallback(self):
        with patch(
            "tenortui.risk_free_rate.requests.get", side_effect=Exception("err")
        ):
            rate, is_live = get_risk_free_rate(fallback=0.04)
        assert rate == 0.04
        assert is_live is False

    def test_http_error_returns_fallback(self):
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("HTTP 500")
        with patch("tenortui.risk_free_rate.requests.get", return_value=resp):
            rate, is_live = get_risk_free_rate()
        assert rate == 0.05
        assert is_live is False
