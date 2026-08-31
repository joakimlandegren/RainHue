"""CLI + core orchestration tests — weather and Hue client mocked."""

import pytest

from rain_hue.__main__ import main
from rain_hue.colors import ColorDecision
from rain_hue.config import Config, HueConfig, Thresholds
from rain_hue.core import run_once
from rain_hue.weather import Forecast


class _FakeHue:
    """Stand-in HueClient recording what was set."""

    def __init__(self):
        self.set_calls = []

    def find_light_id(self, name):
        if name != "Desk Lamp":
            raise RuntimeError(f"Lamp '{name}' not found")
        return "light-1"

    def set_color(self, light_id, xy, brightness):
        self.set_calls.append((light_id, xy, brightness))


def _config():
    return Config(latitude=59.3, longitude=18.1, hue=HueConfig(default_lamp="Desk Lamp"), thresholds=Thresholds())


def test_run_once_end_to_end(mocker):
    mocker.patch(
        "rain_hue.core.fetch_forecast",
        return_value=Forecast(2.0, 0.0, 80.0, 18.0, 10.0),
    )
    hue = _FakeHue()
    result = run_once(_config(), hue_client=hue)

    assert result.decision.reason == "rain (2.0mm)"
    assert hue.set_calls == [("light-1", result.decision.xy, result.decision.brightness)]


def test_run_once_writes_state_file(mocker, tmp_path, monkeypatch):
    """The CLI (and every run_once caller) records the decision for the web UI."""
    state_file = str(tmp_path / "state.json")
    monkeypatch.setenv("RAINHUE_STATE_FILE", state_file)
    mocker.patch(
        "rain_hue.core.fetch_forecast",
        return_value=Forecast(2.0, 0.0, 80.0, 18.0, 10.0),
    )
    run_once(_config(), hue_client=_FakeHue())

    import json

    with open(state_file) as f:
        record = json.load(f)
    assert record["reason"] == "rain (2.0mm)"
    assert record["lamp"] == "Desk Lamp"
    assert record["forecast"]["total_precip_mm"] == 2.0
    assert record["at"]


def test_run_once_lamp_override(mocker):
    mocker.patch("rain_hue.core.fetch_forecast", return_value=Forecast(0.0, 0.0, 0.0, 15.0, 5.0))
    hue = _FakeHue()
    with pytest.raises(RuntimeError, match="not found"):
        run_once(_config(), lamp="Nope", hue_client=hue)


def test_cli_morning(mocker, capsys):
    result = mocker.patch("rain_hue.__main__.run_once")
    from rain_hue.core import RunResult

    result.return_value = RunResult(
        lamp="Desk Lamp",
        decision=ColorDecision((0.457, 0.410), 60.0, "no significant weather"),
        forecast=Forecast(0.0, 0.0, 0.0, 15.0, 5.0),
    )
    code = main(["morning"])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_cli_morning_lamp_override(mocker):
    run = mocker.patch("rain_hue.__main__.run_once")
    from rain_hue.core import RunResult

    run.return_value = RunResult(
        lamp="Kitchen",
        decision=ColorDecision((0.457, 0.410), 60.0, "no significant weather"),
        forecast=Forecast(0.0, 0.0, 0.0, 15.0, 5.0),
    )
    main(["morning", "--lamp", "Kitchen"])
    assert run.call_args.kwargs["lamp"] == "Kitchen"
