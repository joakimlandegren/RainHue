"""State file tests: write, read, corruption fallback, env override."""

import json
import os

import pytest

from rain_hue.state import read_state, state_path, write_state


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = str(tmp_path / "state.json")
    monkeypatch.setenv("RAINHUE_STATE_FILE", path)
    return path


RECORD = {
    "lamp": "Desk Lamp",
    "reason": "rain (2.0mm)",
    "xy": [0.169, 0.321],
    "brightness": 70.0,
    "at": "2026-08-25T06:00:00+00:00",
    "forecast": None,
}


def test_state_path_env_override(state_file):
    assert state_path() == state_file


def test_state_path_default(monkeypatch):
    monkeypatch.delenv("RAINHUE_STATE_FILE", raising=False)
    assert state_path() == os.path.expanduser("~/.rainhue-state.json")


def test_write_then_read_roundtrip(state_file):
    write_state(RECORD)
    assert read_state() == RECORD
    # atomic write leaves no tmp file behind
    assert not os.path.exists(state_file + ".tmp")


def test_read_missing_file_returns_none(state_file):
    assert read_state() is None


def test_read_corrupt_file_returns_none(state_file):
    with open(state_file, "w") as f:
        f.write("{not json")
    assert read_state() is None


def test_read_non_dict_returns_none(state_file):
    with open(state_file, "w") as f:
        json.dump(["a", "list"], f)
    assert read_state() is None


def test_write_failure_does_not_raise(tmp_path, monkeypatch):
    # Point at a path inside a nonexistent directory that cannot be created
    monkeypatch.setenv("RAINHUE_STATE_FILE", str(tmp_path / "no-dir" / "x.json"))
    write_state(RECORD)  # must not raise
