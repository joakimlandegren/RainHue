"""Weather fetch/parse tests with a mocked Open-Meteo API."""

import pytest
import requests

from rain_hue.weather import fetch_forecast


def _payload(probs, precip, snow, temp_max):
    n = max(len(probs), len(precip), len(snow))
    pad = lambda xs: list(xs) + [0] * (n - len(xs))
    return {
        "hourly": {
            "time": [f"2026-08-25T{h:02d}:00" for h in range(n)],
            "precipitation_probability": pad(probs),
            "precipitation": pad(precip),
            "snowfall": pad(snow),
        },
        "daily": {"time": ["2026-08-25"], "temperature_2m_max": [temp_max]},
    }


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_fetch_forecast_aggregates_12h(mocker):
    payload = _payload(
        probs=[10, 80, 40] + [0] * 9,
        precip=[0.5] * 12,
        snow=[0.1] * 12,
        temp_max=23.5,
    )
    mocker.patch("rain_hue.weather.requests.get", return_value=_Resp(payload))

    f = fetch_forecast(59.3, 18.1)
    assert f.total_precip_mm == pytest.approx(6.0)
    assert f.total_snowfall_cm == pytest.approx(1.2)
    assert f.max_precip_probability == 80
    assert f.temp_max_c == 23.5


def test_fetch_forecast_handles_nulls(mocker):
    payload = _payload(probs=[None] * 12, precip=[None] * 12, snow=[None] * 12, temp_max=15.0)
    mocker.patch("rain_hue.weather.requests.get", return_value=_Resp(payload))
    f = fetch_forecast(59.3, 18.1)
    assert f.total_precip_mm == 0
    assert f.total_snowfall_cm == 0


def test_fetch_forecast_http_error(mocker):
    mocker.patch(
        "rain_hue.weather.requests.get",
        side_effect=requests.ConnectionError("down"),
    )
    with pytest.raises(RuntimeError, match="Failed to fetch weather data"):
        fetch_forecast(59.3, 18.1)


def test_fetch_forecast_malformed(mocker):
    mocker.patch("rain_hue.weather.requests.get", return_value=_Resp({"hourly": {}}))
    with pytest.raises(RuntimeError, match="Unexpected response format"):
        fetch_forecast(59.3, 18.1)


def test_fetch_forecast_empty_hourly(mocker):
    payload = _payload(probs=[], precip=[], snow=[], temp_max=15.0)
    mocker.patch("rain_hue.weather.requests.get", return_value=_Resp(payload))
    with pytest.raises(RuntimeError, match="no hourly precipitation data"):
        fetch_forecast(59.3, 18.1)


def test_forecast_has_rain_snow_flags():
    from rain_hue.weather import Forecast

    rain = Forecast(1.0, 0.0, 50.0, 20.0)
    snow = Forecast(1.0, 0.5, 50.0, -2.0)
    dry = Forecast(0.0, 0.0, 0.0, 20.0)
    assert rain.has_rain and not rain.has_snow
    assert snow.has_snow and not snow.has_rain
    assert not dry.has_rain and not dry.has_snow
