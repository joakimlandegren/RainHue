"""API route tests — run_once and weather fetch mocked at the module seam."""

import pytest

from rain_hue.api import create_app
from rain_hue.colors import ColorDecision
from rain_hue.core import RunResult
from rain_hue.weather import Forecast


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _result():
    return RunResult(
        lamp="Desk Lamp",
        decision=ColorDecision((0.169, 0.321), 70.0, "rain (2.0mm)"),
        forecast=Forecast(2.0, 0.0, 80.0, 18.0, 10.0),
    )


def test_set_color_ok(client, mocker):
    mocker.patch("rain_hue.api.run_once", return_value=_result())
    resp = client.post("/set-color")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["lamp"] == "Desk Lamp"
    assert body["reason"] == "rain (2.0mm)"
    assert body["forecast"]["total_precip_mm"] == 2.0


def test_set_color_lamp_override_passed_through(client, mocker):
    run = mocker.patch("rain_hue.api.run_once", return_value=_result())
    client.post("/set-color?lamp=Kitchen")
    assert run.call_args.kwargs["lamp"] == "Kitchen"


def test_set_color_failure_is_502(client, mocker):
    mocker.patch("rain_hue.api.run_once", side_effect=RuntimeError("hue down"))
    resp = client.post("/set-color")
    assert resp.status_code == 502
    assert "hue down" in resp.get_json()["error"]


def test_weather_ok(client, mocker):
    mocker.patch(
        "rain_hue.api.fetch_forecast",
        return_value=Forecast(1.5, 0.0, 60.0, 21.0, 12.0),
    )
    resp = client.get("/weather")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total_precip_mm"] == 1.5
    assert body["temp_max_c"] == 21.0


def test_weather_failure_is_502(client, mocker):
    mocker.patch("rain_hue.api.fetch_forecast", side_effect=RuntimeError("meteo down"))
    resp = client.get("/weather")
    assert resp.status_code == 502
