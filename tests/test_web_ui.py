"""Tests for the web-UI endpoints: /api/status, /api/mode/<name>, /api/morning, GET /."""

import pytest

from rain_hue.api import create_app
from rain_hue.colors import MODES
from rain_hue.core import RunResult
from rain_hue.colors import ColorDecision
from rain_hue.weather import Forecast
from rain_hue.hue import HueError


class FakeHue:
    """HueClient stand-in with lamp state."""

    def __init__(self, fail=False):
        self.fail = fail
        self.set_calls = []
        self._on = True

    def find_light_id(self, name):
        if self.fail:
            raise HueError("hue unreachable")
        return "light-1"

    def set_color(self, light_id, xy, brightness):
        if self.fail:
            raise HueError("hue unreachable")
        self.set_calls.append((light_id, xy, brightness))
        self._on = True

    def get_light_status(self, light_id):
        if self.fail:
            raise HueError("hue unreachable")
        xy = self.set_calls[-1][1] if self.set_calls else (0.3, 0.3)
        bri = self.set_calls[-1][2] if self.set_calls else 55.0
        return {"name": "Desk Lamp", "on": self._on, "xy": list(xy), "brightness": bri}


@pytest.fixture
def hue():
    return FakeHue()


@pytest.fixture(autouse=True)
def state_file(tmp_path, monkeypatch):
    """Isolate the state file per test."""
    path = str(tmp_path / "state.json")
    monkeypatch.setenv("RAINHUE_STATE_FILE", path)
    return path


@pytest.fixture
def client(hue):
    app = create_app(hue_client=hue)
    app.config.update(TESTING=True)
    return app.test_client()


class TestIndex:
    def test_page_serves(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "RainHue" in html
        assert "/api/status" in html
        assert "/api/morning" in html


class TestStatus:
    def test_status_with_reachable_lamp(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["lamp"]["name"] == "Desk Lamp"
        assert body["lamp"]["on"] is True
        assert body["lamp"]["xy"] == [0.3, 0.3]
        assert body["lamp_error"] is None
        assert body["last_decision"] is None
        assert body["modes"] == sorted(MODES.keys())

    def test_status_degrades_when_lamp_unreachable(self):
        app = create_app(hue_client=FakeHue(fail=True))
        app.config.update(TESTING=True)
        c = app.test_client()
        resp = c.get("/api/status")
        assert resp.status_code == 200  # status endpoint itself must not 5xx
        body = resp.get_json()
        assert body["lamp_error"] == "hue unreachable"
        assert body["lamp"]["on"] is None


class TestModes:
    def test_mode_applies_preset_and_records_decision(self, client, hue):
        resp = client.post("/api/mode/rain")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["reason"] == "manual mode: rain"
        assert hue.set_calls == [("light-1", tuple(body["xy"]), body["brightness"])]

        # status now reports the decision
        status = client.get("/api/status").get_json()
        assert status["last_decision"]["reason"] == "manual mode: rain"

    def test_all_documented_modes_exist(self, client):
        for mode in ["rain", "snow", "heat", "extreme", "neutral"]:
            resp = client.post(f"/api/mode/{mode}")
            assert resp.status_code == 200, mode

    def test_unknown_mode_404(self, client):
        resp = client.post("/api/mode/apocalypse")
        assert resp.status_code == 404
        assert resp.get_json()["modes"] == sorted(MODES.keys())

    def test_mode_hue_failure_is_502(self):
        app = create_app(hue_client=FakeHue(fail=True))
        app.config.update(TESTING=True)
        c = app.test_client()
        resp = c.post("/api/mode/rain")
        assert resp.status_code == 502


class TestMorning:
    def test_morning_runs_logic_and_records(self, client, hue, mocker):
        mocker.patch(
            "rain_hue.core.fetch_forecast",
            return_value=Forecast(2.0, 0.0, 80.0, 18.0),
        )
        resp = client.post("/api/morning")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["reason"] == "rain (2.0mm)"
        assert body["forecast"]["total_precip_mm"] == 2.0
        assert len(hue.set_calls) == 1

        status = client.get("/api/status").get_json()
        assert status["last_decision"]["reason"] == "rain (2.0mm)"
        assert status["last_decision"]["forecast"]["temp_max_c"] == 18.0

    def test_morning_weather_failure_is_502(self, client, mocker):
        mocker.patch(
            "rain_hue.core.fetch_forecast",
            side_effect=RuntimeError("meteo down"),
        )
        resp = client.post("/api/morning")
        assert resp.status_code == 502
        assert "meteo down" in resp.get_json()["error"]


class TestStateSharing:
    def test_status_reads_state_file_written_by_another_process(self, client, state_file):
        # Simulate a cron CLI run: write the file directly, then ask the API.
        from rain_hue.state import write_state

        write_state({"lamp": "Desk Lamp", "reason": "snow (1.0cm)", "xy": [0.24, 0.24],
                     "brightness": 65.0, "at": "2026-08-25T06:00:00+00:00", "forecast": None})
        body = client.get("/api/status").get_json()
        assert body["last_decision"]["reason"] == "snow (1.0cm)"

    def test_status_falls_back_to_memory_when_file_corrupt(self, client, hue, state_file):
        # API mode trigger writes both memory + file
        client.post("/api/mode/heat")
        # Corrupt the file -> status must fall back to the in-memory record
        with open(state_file, "w") as f:
            f.write("{corrupt")
        body = client.get("/api/status").get_json()
        assert body["last_decision"]["reason"] == "manual mode: heat"

    def test_status_none_when_no_file_and_no_memory(self, client):
        assert client.get("/api/status").get_json()["last_decision"] is None
