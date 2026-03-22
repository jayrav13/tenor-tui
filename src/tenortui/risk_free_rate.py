import requests

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES = "DTB3"
FRED_API_KEY = "DEMO_KEY"

_cached_rate: float | None = None
_cached_is_live: bool = False


def get_risk_free_rate(fallback: float = 0.05) -> tuple[float, bool]:
    global _cached_rate, _cached_is_live
    if _cached_rate is not None:
        return _cached_rate, _cached_is_live

    try:
        resp = requests.get(
            FRED_URL,
            params={
                "series_id": FRED_SERIES,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 10,
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        for obs in data.get("observations", []):
            if obs["value"] == ".":
                continue
            rate = float(obs["value"]) / 100.0
            _cached_rate = rate
            _cached_is_live = True
            return rate, True

        return fallback, False
    except Exception:
        return fallback, False
