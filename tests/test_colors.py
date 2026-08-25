"""Exhaustive coverage of the locked color-decision logic."""

import pytest

from rain_hue.colors import (
    _COLD_WHITE,
    _DEEP_BLUE,
    _LIGHT_BLUE,
    _NEUTRAL_WARM_WHITE,
    _ORANGE,
    _RED,
    decide_color,
)
from rain_hue.config import Thresholds
from rain_hue.weather import Forecast

T = Thresholds()  # defaults: rain 0.1/5.0mm, snow 0.1/2.0cm, orange >25, red >30


def f(precip=0.0, snow=0.0, temp=15.0, prob=0.0) -> Forecast:
    return Forecast(
        total_precip_mm=precip,
        total_snowfall_cm=snow,
        max_precip_probability=prob,
        temp_max_c=temp,
    )


class TestRain:
    def test_light_rain_is_light_blue(self):
        d = decide_color(f(precip=1.0), T)
        assert d.xy == _LIGHT_BLUE
        assert "rain" in d.reason

    def test_rain_at_min_threshold_counts(self):
        d = decide_color(f(precip=0.1), T)
        assert d.xy == _LIGHT_BLUE

    def test_below_min_rain_is_neutral(self):
        d = decide_color(f(precip=0.05), T)
        assert d.xy == _NEUTRAL_WARM_WHITE

    def test_heavy_rain_is_deep_blue(self):
        d = decide_color(f(precip=5.0), T)
        assert d.xy == _DEEP_BLUE
        assert "heavy" in d.reason

    def test_very_heavy_rain(self):
        d = decide_color(f(precip=12.0), T)
        assert d.xy == _DEEP_BLUE

    def test_heavy_rain_brighter_than_light(self):
        light = decide_color(f(precip=1.0), T)
        heavy = decide_color(f(precip=8.0), T)
        assert heavy.brightness > light.brightness


class TestSnow:
    def test_snow_is_cold_white(self):
        d = decide_color(f(snow=0.5), T)
        assert d.xy == _COLD_WHITE

    def test_snow_at_min_threshold_counts(self):
        d = decide_color(f(snow=0.1), T)
        assert d.xy == _COLD_WHITE

    def test_below_min_snow_is_neutral(self):
        d = decide_color(f(snow=0.05), T)
        assert d.xy == _NEUTRAL_WARM_WHITE

    def test_heavy_snow_brighter(self):
        light = decide_color(f(snow=0.5), T)
        heavy = decide_color(f(snow=3.0), T)
        assert heavy.xy == _COLD_WHITE
        assert heavy.brightness > light.brightness
        assert "heavy" in heavy.reason

    def test_snow_beats_rain_in_wintry_mix(self):
        # Both rain and snow amounts present -> snow wins (wintry mix)
        d = decide_color(f(precip=3.0, snow=1.0), T)
        assert d.xy == _COLD_WHITE


class TestHeat:
    def test_orange_above_25(self):
        d = decide_color(f(temp=26.0), T)
        assert d.xy == _ORANGE

    def test_red_above_30(self):
        d = decide_color(f(temp=31.0), T)
        assert d.xy == _RED

    def test_boundary_25_is_neutral(self):
        # Locked: ">25" so exactly 25 -> neutral
        d = decide_color(f(temp=25.0), T)
        assert d.xy == _NEUTRAL_WARM_WHITE

    def test_boundary_30_is_orange(self):
        # Locked: ">30" red, so exactly 30 -> orange
        d = decide_color(f(temp=30.0), T)
        assert d.xy == _ORANGE


class TestPriority:
    def test_rain_beats_extreme_heat(self):
        d = decide_color(f(precip=2.0, temp=35.0), T)
        assert d.xy == _LIGHT_BLUE

    def test_snow_beats_extreme_heat(self):
        d = decide_color(f(snow=1.0, temp=35.0), T)
        assert d.xy == _COLD_WHITE

    def test_no_precip_no_heat_is_neutral(self):
        d = decide_color(f(temp=10.0), T)
        assert d.xy == _NEUTRAL_WARM_WHITE
        assert "no significant weather" in d.reason


class TestCustomThresholds:
    def test_custom_rain_threshold(self):
        t = Thresholds(rain_min_mm=2.0)
        assert decide_color(f(precip=1.0), t).xy == _NEUTRAL_WARM_WHITE
        assert decide_color(f(precip=3.0), t).xy == _LIGHT_BLUE

    def test_custom_heat_threshold(self):
        t = Thresholds(temp_orange_c=20.0, temp_red_c=28.0)
        assert decide_color(f(temp=21.0), t).xy == _ORANGE
        assert decide_color(f(temp=29.0), t).xy == _RED
