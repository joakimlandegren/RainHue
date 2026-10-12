"""Local morning regressions: dummy credentials and mocked HTTP only."""
import os
from pathlib import Path
import subprocess

import pytest
import requests

from rain_hue.config import Config, HueConfig
from rain_hue.core import run_once
from rain_hue.hue import HueClient, HueError
from rain_hue.weather import Forecast
from tests.test_hue import _Resp

BRIDGE = "https://192.168.68.90"
LIGHT = {"id": "barnhall-id", "metadata": {"name": "Barnhall"}}


def local_config():
    return HueConfig(username="dummy-key", access_token="dummy-token",
                     refresh_token="dummy-refresh", client_id="dummy", client_secret="dummy",
                     local_bridge=BRIDGE)


def test_local_requests_use_bridge_key_without_cloud_auth(mocker):
    request = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {"data": [LIGHT]}))
    refresh = mocker.patch("rain_hue.hue.requests.post")
    assert HueClient(local_config()).find_light_id("barnhall") == "barnhall-id"
    assert request.call_args.args[1] == BRIDGE + "/clip/v2/resource/light"
    assert request.call_args.kwargs["headers"]["hue-application-key"] == "dummy-key"
    assert "Authorization" not in request.call_args.kwargs["headers"]
    assert request.call_args.kwargs["verify"] is False
    refresh.assert_not_called()


@pytest.mark.parametrize("status", [401, 403, 500])
def test_local_http_failure_never_refreshes(mocker, status):
    request = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(status, text="failure"))
    refresh = mocker.patch("rain_hue.hue.requests.post")
    with pytest.raises(HueError):
        HueClient(local_config()).list_lights()
    refresh.assert_not_called()
    assert request.call_count == 1


@pytest.mark.parametrize("operation", ["list", "set", "get"])
def test_clip_error_payload_is_not_success(mocker, operation):
    mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {
        "errors": [{"description": "bridge rejected command"}], "data": [LIGHT]}))
    client = HueClient(local_config())
    with pytest.raises(HueError, match="bridge rejected command"):
        if operation == "list":
            client.list_lights()
        elif operation == "set":
            client.set_color("barnhall-id", (0.2, 0.3), 60)
        else:
            client.get_light_status("barnhall-id")


def test_duplicate_lamp_does_not_actuate(mocker):
    lights = [LIGHT, {"id": "other-id", "metadata": {"name": "BARNHALL"}}]
    request = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {"data": lights}))
    with pytest.raises(HueError, match="[Aa]mbiguous"):
        HueClient(local_config()).find_light_id("Barnhall")
    assert all(call.args[0] == "GET" for call in request.call_args_list)


def status_payload(on=True, x=0.2, y=0.3, brightness=60.0):
    return {"data": [{**LIGHT, "on": {"on": on}, "color": {"xy": {"x": x, "y": y}},
                      "dimming": {"brightness": brightness}}]}


def test_local_put_is_verified_with_quantization_tolerance(mocker):
    request = mocker.patch("rain_hue.hue.requests.request", side_effect=[
        _Resp(200, {"data": [{"rid": "barnhall-id"}]}),
        _Resp(200, status_payload(x=0.2003, y=0.3003, brightness=59.8))])
    HueClient(local_config()).set_color("barnhall-id", (0.2, 0.3), 60)
    assert [call.args[0] for call in request.call_args_list] == ["PUT", "GET"]
    assert all(call.args[1] == BRIDGE + "/clip/v2/resource/light/barnhall-id"
               for call in request.call_args_list)


@pytest.mark.parametrize("payload", [status_payload(on=False), status_payload(x=0.4),
                                      status_payload(brightness=40), {"data": []}])
def test_readback_mismatch_cannot_write_success_state(mocker, payload):
    from rain_hue.colors import ColorDecision
    mocker.patch("rain_hue.core.fetch_forecast", return_value=Forecast(0, 0, 0, 15, 5))
    mocker.patch("rain_hue.core.decide_color", return_value=ColorDecision((0.2, 0.3), 60, "fresh"))
    write = mocker.patch("rain_hue.core.write_state")
    mocker.patch("time.sleep")
    mocker.patch("rain_hue.hue.requests.request", side_effect=[
        _Resp(200, {"data": [LIGHT]}), _Resp(200, {"data": []})] + [_Resp(200, payload)] * 5)
    with pytest.raises(HueError):
        run_once(Config(hue=local_config()), lamp="Barnhall")
    write.assert_not_called()


def test_local_connection_failure_is_error(mocker):
    mocker.patch("rain_hue.hue.requests.request", side_effect=requests.ConnectionError("offline"))
    with pytest.raises(HueError, match="request failed"):
        HueClient(local_config()).list_lights()


def wrapper_run(tmp_path, exit_code, output):
    home = tmp_path / "home"
    project = home / "projects" / "RainHue"
    python = project / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text(f"#!/bin/sh\n"
                      'test "$*" = "-m rain_hue morning --local-bridge https://192.168.68.90 --lamp Barnhall --script" || exit 99\n'
                      f"printf '%s\\n' '{output}'\nexit {exit_code}\n")
    python.chmod(0o755)
    (home / ".rainhue-state.json").write_text('{"reason":"STALE SUCCESS","xy":[0.2,0.3],"brightness":60}')
    script = Path(__file__).resolve().parents[1] / "ops" / "rainhue-morning.sh"
    assert script.exists(), "Replacement morning wrapper is required"
    return subprocess.run(["bash", str(script)], env={**os.environ, "HOME": str(home)},
                          capture_output=True, text=True)


def test_wrapper_cli_failure_does_not_report_stale_state(tmp_path):
    result = wrapper_run(tmp_path, 7, "bridge failure")
    assert result.returncode == 7
    assert "STALE SUCCESS" not in result.stdout
    assert "RainHue morning:" not in result.stdout


def test_wrapper_outputs_only_current_cli_message(tmp_path):
    message = "🌅 RainHue morning: Barnhall: rain (2.0mm); xy=(0.17, 0.32) brightness=70"
    result = wrapper_run(tmp_path, 0, message)
    assert result.returncode == 0
    assert result.stdout.strip() == message


def test_cli_script_uses_explicit_local_config_and_fresh_result(mocker, capsys):
    from rain_hue.__main__ import main
    from rain_hue.colors import ColorDecision
    from rain_hue.core import RunResult
    run = mocker.patch("rain_hue.__main__.run_once", return_value=RunResult(
        lamp="Barnhall", decision=ColorDecision((0.2, 0.3), 60, "fresh rain"), forecast=None))
    assert main(["morning", "--local-bridge", BRIDGE, "--lamp", "Barnhall", "--script"]) == 0
    assert run.call_args.args[0].hue.local_bridge == BRIDGE
    message = capsys.readouterr().out
    assert message.startswith("🌅 RainHue morning: Barnhall: fresh rain;")
    assert len(message.splitlines()) == 1


@pytest.mark.parametrize("url", ["http://192.168.68.90", "https://api.meethue.com",
                                "https://8.8.8.8", "https://192.168.68.90/route"])
def test_self_signed_tls_exception_cannot_escape_local_lan(url, mocker):
    from dataclasses import replace
    request = mocker.patch("rain_hue.hue.requests.request")
    with pytest.raises(HueError, match="private LAN"):
        HueClient(replace(local_config(), local_bridge=url))
    request.assert_not_called()


def test_cloud_default_preserves_tls_verification_and_auth(mocker):
    request = mocker.patch("rain_hue.hue.requests.request", return_value=_Resp(200, {"data": [LIGHT]}))
    HueClient(HueConfig(username="dummy-key", access_token="dummy-token")).list_lights()
    assert request.call_args.args[1] == "https://api.meethue.com/route/clip/v2/resource/light"
    assert request.call_args.kwargs["verify"] is True
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer dummy-token"


@pytest.mark.parametrize("error", [RuntimeError("weather unavailable"), HueError("bridge unavailable")])
def test_cli_failure_has_no_success_message(mocker, capsys, error):
    from rain_hue.__main__ import main
    mocker.patch("rain_hue.__main__.run_once", side_effect=error)
    with pytest.raises(RuntimeError):
        main(["morning", "--local-bridge", BRIDGE, "--script"])
    assert capsys.readouterr().out == ""


def test_local_core_writes_fresh_state_only_after_matching_readback(mocker, tmp_path, monkeypatch):
    import json
    from rain_hue.colors import decide_color
    config = Config(hue=local_config())
    forecast = Forecast(2, 0, 80, 18, 10)
    decision = decide_color(forecast, config.thresholds)
    state = tmp_path / "state.json"
    state.write_text('{"reason":"stale"}')
    monkeypatch.setenv("RAINHUE_STATE_FILE", str(state))
    mocker.patch("rain_hue.core.fetch_forecast", return_value=forecast)
    refresh = mocker.patch("rain_hue.hue.requests.post")
    request = mocker.patch("rain_hue.hue.requests.request", side_effect=[
        _Resp(200, {"data": [LIGHT]}), _Resp(200, {"data": []}),
        _Resp(200, status_payload(x=decision.xy[0], y=decision.xy[1], brightness=decision.brightness))])
    result = run_once(config, lamp="Barnhall")
    record = json.loads(state.read_text())
    assert record["reason"] == result.decision.reason
    assert record["lamp"] == "Barnhall"
    assert record["xy"] == list(decision.xy)
    assert record["at"]
    assert [call.args[0] for call in request.call_args_list] == ["GET", "PUT", "GET"]
    for call in request.call_args_list:
        assert call.args[1].startswith(BRIDGE + "/clip/v2/resource/light")
        assert "Authorization" not in call.kwargs["headers"]
        assert call.kwargs["verify"] is False
        assert call.kwargs["allow_redirects"] is False
    refresh.assert_not_called()
