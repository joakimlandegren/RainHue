"""Bounded retries for transient weather failures; no real lamp writes."""
from unittest.mock import call

import pytest
import requests

from rain_hue.core import run_once
from rain_hue.config import Config, HueConfig
from rain_hue.weather import fetch_forecast
from tests.test_weather import _Resp, _payload


def http_error(status):
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"HTTP {status}", response=response)


def good_response():
    return _Resp(_payload([70] * 12, [0.1] * 12, [0] * 12, 10.0))


def test_temporary_503_recovers_on_third_attempt(mocker):
    get = mocker.patch("rain_hue.weather.requests.get", side_effect=[
        http_error(503), http_error(503), good_response()])
    sleep = mocker.patch("rain_hue.weather.time.sleep")
    forecast = fetch_forecast(59.33, 18.07)
    assert forecast.total_precip_mm == pytest.approx(1.2)
    assert get.call_count == 3
    assert sleep.call_args_list == [call(2), call(5)]
    assert all(c.kwargs["timeout"] == 15.0 for c in get.call_args_list)


@pytest.mark.parametrize("error", [
    http_error(429), http_error(500), http_error(502), http_error(503), http_error(504),
    requests.Timeout("timeout"), requests.ConnectionError("offline")])
def test_transient_failure_is_bounded_and_does_not_touch_lamp(mocker, error):
    get = mocker.patch("rain_hue.weather.requests.get", side_effect=error)
    sleep = mocker.patch("rain_hue.weather.time.sleep")
    hue = mocker.patch("rain_hue.core.HueClient")
    write = mocker.patch("rain_hue.core.write_state")
    config = Config(latitude=59.33, longitude=18.07, hue=HueConfig(
        client_id="dummy", client_secret="dummy", access_token="dummy",
        refresh_token="dummy", username="dummy", default_lamp="Barnhall"))
    with pytest.raises(RuntimeError, match="Failed to fetch weather data"):
        run_once(config, lamp="Barnhall")
    assert get.call_count == 3
    assert sleep.call_args_list == [call(2), call(5)]
    hue.assert_not_called()
    write.assert_not_called()


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_http_error_is_not_retried(mocker, status):
    get = mocker.patch("rain_hue.weather.requests.get", side_effect=http_error(status))
    sleep = mocker.patch("rain_hue.weather.time.sleep")
    with pytest.raises(RuntimeError, match="Failed to fetch weather data"):
        fetch_forecast(59.33, 18.07)
    assert get.call_count == 1
    sleep.assert_not_called()


def test_success_needs_only_one_attempt(mocker):
    get = mocker.patch("rain_hue.weather.requests.get", return_value=good_response())
    sleep = mocker.patch("rain_hue.weather.time.sleep")
    fetch_forecast(59.33, 18.07)
    assert get.call_count == 1
    sleep.assert_not_called()
