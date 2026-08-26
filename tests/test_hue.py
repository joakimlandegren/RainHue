"""Hue remote client tests — all HTTP mocked."""

import pytest
import requests

from rain_hue.config import HueConfig
from rain_hue.hue import HueClient, HueError


def _cfg(**kw):
    base = dict(
        client_id="cid",
        client_secret="sec",
        access_token="old-token",
        refresh_token="old-refresh",
        username="bridgeuser",
        base_url="https://api.meethue.com",
        default_lamp="Desk Lamp",
    )
    base.update(kw)
    return HueConfig(**base)


class _Resp:
    def __init__(self, status, payload=None, text=None):
        self.status_code = status
        self._payload = payload or {}
        self.text = text if text is not None else ("" if payload is None else "json")

    def json(self):
        return self._payload


LIGHTS = {
    "data": [
        {"id": "light-1", "metadata": {"name": "Desk Lamp"}},
        {"id": "light-2", "metadata": {"name": "Kitchen"}},
    ]
}


def test_find_light_id(mocker):
    mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, LIGHTS))
    client = HueClient(_cfg())
    assert client.find_light_id("desk lamp") == "light-1"  # case-insensitive


def test_find_light_id_missing_lists_available(mocker):
    mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, LIGHTS))
    client = HueClient(_cfg())
    with pytest.raises(HueError, match="Available: Desk Lamp, Kitchen"):
        client.find_light_id("Bedroom")


def test_set_color_puts_clipv2_body(mocker):
    req = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {"data": []}))
    client = HueClient(_cfg())
    client.set_color("light-1", (0.17, 0.32), 70.0)

    args, kwargs = req.call_args
    assert args[0] == "PUT"
    # Remote v2 API: /route/clip/v2/... with the bridge user in the
    # hue-application-key header (verified against production).
    assert args[1] == "https://api.meethue.com/route/clip/v2/resource/light/light-1"
    assert kwargs["headers"]["Authorization"] == "Bearer old-token"
    assert kwargs["headers"]["hue-application-key"] == "bridgeuser"
    assert kwargs["json"] == {
        "on": {"on": True},
        "color": {"xy": {"x": 0.17, "y": 0.32}},
        "dimming": {"brightness": 70.0},
    }


def test_list_lights_uses_correct_remote_path(mocker):
    """Regression: remote API is /route/clip/v2/... (no /api/<user>/api prefix)."""
    req = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, LIGHTS))
    client = HueClient(_cfg())
    client.list_lights()
    url = req.call_args.args[1]
    assert url == "https://api.meethue.com/route/clip/v2/resource/light"
    assert "/api/clip" not in url


def test_get_light_status_uses_correct_remote_path(mocker):
    payload = {"data": [{"metadata": {"name": "Desk Lamp"}, "on": {"on": True},
                         "color": {"xy": {"x": 0.3, "y": 0.3}}, "dimming": {"brightness": 55.0}}]}
    req = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, payload))
    client = HueClient(_cfg())
    status = client.get_light_status("light-1")
    assert req.call_args.args[1] == "https://api.meethue.com/route/clip/v2/resource/light/light-1"
    assert status["on"] is True


def test_list_lights_error_list_raises_hueerror(mocker):
    """Regression: the old wrong path returned a JSON list of error objects,
    which crashed list_lights with AttributeError. Now raises HueError with
    the error description."""
    error_list = [{"error": {"type": 1, "address": "/lights", "description": "unauthorized user"}}]
    mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, error_list))
    client = HueClient(_cfg())
    with pytest.raises(HueError, match="unauthorized user"):
        client.list_lights()


def test_brightness_clamped(mocker):
    req = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {}))
    client = HueClient(_cfg())
    client.set_color("light-1", (0.2, 0.2), 250.0)
    assert req.call_args.kwargs["json"]["dimming"]["brightness"] == 100.0


def test_401_triggers_refresh_and_retry(mocker):
    # First call 401, then retry 200
    req = mocker.patch(
        "rain_hue.hue.requests.request",
        side_effect=[_Resp(401, text="unauthorized"), _Resp(200, LIGHTS)],
    )
    post = mocker.patch(
        "rain_hue.hue.requests.post",
        return_value=_Resp(200, {"access_token": "new-token", "refresh_token": "new-refresh"}),
    )

    client = HueClient(_cfg())
    assert client.find_light_id("Desk Lamp") == "light-1"
    assert req.call_count == 2
    # Retry used the new token
    assert req.call_args.kwargs["headers"]["Authorization"] == "Bearer new-token"
    # Refresh request hit the OAuth endpoint with the old refresh token
    assert post.call_args.args[0] == "https://api.meethue.com/oauth2/token"
    assert post.call_args.kwargs["data"]["refresh_token"] == "old-refresh"


def test_401_without_client_creds_fails_clear(mocker):
    mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(401, text="unauthorized"))
    client = HueClient(_cfg(client_id="", client_secret=""))
    with pytest.raises(HueError, match="HUE_CLIENT_ID"):
        client.list_lights()


def test_http_error_raises(mocker):
    mocker.patch(
        "rain_hue.hue.requests.request",
        side_effect=requests.ConnectionError("down"),
    )
    client = HueClient(_cfg())
    with pytest.raises(HueError, match="request failed"):
        client.list_lights()


def test_missing_username_fails_fast(mocker):
    client = HueClient(_cfg(username=""))
    with pytest.raises(HueError, match="HUE_USERNAME"):
        client.list_lights()
