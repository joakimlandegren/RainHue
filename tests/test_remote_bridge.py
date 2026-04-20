"""Tests for the RemoteBridge class.

RemoteBridge is a subclass of phue.Bridge that performs HTTP requests to a
remote Philips Hue API.  It stores uri, username, and token; uses requests
for GET/PUT/POST/DELETE; and raises PhueRequestTimeout on socket.timeout.
"""

import json
import socket
from unittest.mock import patch, MagicMock

import pytest
from phue import PhueRequestTimeout

from rain_hue.remote_bridge import RemoteBridge


def _make_bridge(uri="https://api.hue.example.com/", username="testuser", token="test-token-123"):
    """Create a RemoteBridge without hitting real network or file system."""
    with patch.object(RemoteBridge, "connect", return_value=None):
        bridge = RemoteBridge(uri=uri, username=username, token=token)
    return bridge


class TestRemoteBridgeInit:
    """Tests for RemoteBridge constructor."""

    def test_init_sets_uri_and_username(self):
        """Verify constructor stores uri, username, and token."""
        bridge = _make_bridge(
            uri="https://api.hue.example.com/",
            username="myuser",
            token="my-secret-token",
        )

        assert bridge.uri == "https://api.hue.example.com/"
        assert bridge.username == "myuser"
        assert bridge.token == "my-secret-token"


class TestGetLightObjects:
    """Tests for RemoteBridge.get_light_objects()."""

    @patch("rain_hue.remote_bridge.requests.get")
    def test_get_light_objects_by_name(self, mock_get):
        """Mock the HTTP request, verify lights dict is populated by name."""
        bridge = _make_bridge()

        lights_response = {
            "1": {"name": "Desk Lamp", "state": {"on": True}},
            "2": {"name": "Living Room", "state": {"on": False}},
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(lights_response)
        mock_get.return_value = mock_response

        result = bridge.get_light_objects("name")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "lights" in url
        assert bridge.username in url

        assert "Desk Lamp" in result
        assert "Living Room" in result
        assert len(result) == 2


class TestSetLight:
    """Tests for RemoteBridge.set_light()."""

    @patch("rain_hue.remote_bridge.requests.put")
    def test_set_light_by_id(self, mock_put):
        """Mock request, verify PUT is called with correct URL and data."""
        bridge = _make_bridge(
            uri="https://api.hue.example.com/",
            username="testuser",
            token="test-token",
        )

        mock_response = MagicMock()
        mock_response.text = json.dumps([{"success": {"/lights/1/state/on": True}}])
        mock_put.return_value = mock_response

        bridge.set_light(1, {"on": True, "bri": 254})

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        url = call_args[0][0]
        assert "/lights/1/state" in url
        assert "testuser" in url

        data = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("data")
        parsed = json.loads(data)
        assert parsed["on"] is True
        assert parsed["bri"] == 254

        headers = call_args[1].get("headers", {})
        assert "Bearer" in headers.get("Authorization", "")

    @patch("rain_hue.remote_bridge.requests.put")
    def test_set_light_by_name(self, mock_put):
        """Mock request and get_light_id_by_name, verify correct conversion."""
        bridge = _make_bridge(
            uri="https://api.hue.example.com/",
            username="testuser",
            token="test-token",
        )

        mock_response = MagicMock()
        mock_response.text = json.dumps([{"success": {"/lights/3/state/on": True}}])
        mock_put.return_value = mock_response

        with patch.object(bridge, "get_light_id_by_name", return_value=3):
            bridge.set_light("Desk Lamp", {"on": True})

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        url = call_args[0][0]
        assert "/lights/3/state" in url


class TestRequest:
    """Tests for RemoteBridge.request() utility method."""

    @patch("rain_hue.remote_bridge.requests.get")
    def test_request_get(self, mock_get):
        """Verify GET uses correct content-type header (x-www-form-urlencoded)."""
        bridge = _make_bridge(token="my-token")

        mock_response = MagicMock()
        mock_response.text = json.dumps({"result": "ok"})
        mock_get.return_value = mock_response

        result = bridge.request(
            "GET",
            "https://api.hue.example.com/bridge/testuser/lights/",
            auth_token="my-token",
        )

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        headers = call_args[1].get("headers", {})

        assert headers["Content-type"] == "application/x-www-form-urlencoded"
        assert "Bearer my-token" in headers["Authorization"]

        assert result == {"result": "ok"}

    @patch("rain_hue.remote_bridge.requests.get")
    def test_request_timeout(self, mock_get):
        """Mock socket.timeout, verify PhueRequestTimeout is raised."""
        bridge = _make_bridge(token="my-token")

        mock_get.side_effect = socket.timeout("Connection timed out")

        with pytest.raises(PhueRequestTimeout):
            bridge.request(
                "GET",
                "https://api.hue.example.com/bridge/testuser/lights/",
                auth_token="my-token",
            )
