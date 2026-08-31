"""Color-decision logic for RainHue v2 (locked requirements).

Priority (locked):
1. Precipitation in the next 12h beats temperature.
   - Rain -> blue; heavier rain -> deeper / more saturated blue.
   - Snow -> cold white; heavier snow -> brighter cold white.
2. No precipitation and min temp below freezing -> cold white.
3. Heat override only for extremes (no precip):
   - max temp > 30°C -> red; > 25°C -> orange.
4. Otherwise -> neutral warm-white.

Colors are expressed for the Hue CLIP v2 API: CIE xy + brightness (0-100).
"""

from dataclasses import dataclass

from .config import Thresholds
from .weather import Forecast


@dataclass(frozen=True)
class ColorDecision:
    """A decided lamp state plus the reason for it."""

    xy: tuple[float, float]
    brightness: float  # 0-100 (CLIP v2 dimming scale)
    reason: str


# CIE xy presets.
_LIGHT_BLUE = (0.169, 0.321)
_DEEP_BLUE = (0.136, 0.040)
_COLD_WHITE = (0.240, 0.240)  # cold white (snow / freezing)
_NEUTRAL_WARM_WHITE = (0.457, 0.410)
_ORANGE = (0.600, 0.380)
_RED = (0.675, 0.322)

# Manual trigger modes for the web UI: name -> a representative ColorDecision.
# These reuse the same presets as the weather logic (rain = moderate rain,
# snow = moderate snow, heat/extreme = the two heat bands).
MODES: dict[str, "ColorDecision"] = {}


def _register_modes() -> None:
    MODES.update(
        {
            "rain": ColorDecision(_LIGHT_BLUE, 70.0, "manual mode: rain"),
            "snow": ColorDecision(_COLD_WHITE, 65.0, "manual mode: snow"),
            "freezing": ColorDecision(_COLD_WHITE, 60.0, "manual mode: freezing"),
            "heat": ColorDecision(_ORANGE, 90.0, "manual mode: heat"),
            "extreme": ColorDecision(_RED, 100.0, "manual mode: extreme heat"),
            "neutral": ColorDecision(_NEUTRAL_WARM_WHITE, 60.0, "manual mode: neutral"),
        }
    )


def decide_color(forecast: Forecast, thresholds: Thresholds) -> ColorDecision:
    """Decide the lamp color for a forecast. Pure function — fully testable."""
    # 1. Precipitation beats temperature. Snow takes precedence over rain when
    #    both occur (wintry mix looks like snow).
    if forecast.total_snowfall_cm >= thresholds.snow_min_cm:
        if forecast.total_snowfall_cm >= thresholds.snow_heavy_cm:
            return ColorDecision(_COLD_WHITE, 100.0, f"heavy snow ({forecast.total_snowfall_cm:.1f}cm)")
        return ColorDecision(_COLD_WHITE, 65.0, f"snow ({forecast.total_snowfall_cm:.1f}cm)")

    if forecast.total_precip_mm >= thresholds.rain_min_mm:
        if forecast.total_precip_mm >= thresholds.rain_heavy_mm:
            return ColorDecision(_DEEP_BLUE, 100.0, f"heavy rain ({forecast.total_precip_mm:.1f}mm)")
        return ColorDecision(_LIGHT_BLUE, 70.0, f"rain ({forecast.total_precip_mm:.1f}mm)")

    # 2. Freezing cold (only reached with no precipitation). Ordered before
    #    the heat bands; sub-zero min and heat can't really co-occur.
    if forecast.temp_min_c < thresholds.temp_freezing_c:
        return ColorDecision(_COLD_WHITE, 60.0, f"freezing (min {forecast.temp_min_c:.1f}°C)")

    # 3. Heat extremes (only reached with no precipitation).
    if forecast.temp_max_c > thresholds.temp_red_c:
        return ColorDecision(_RED, 100.0, f"extreme heat ({forecast.temp_max_c:.1f}°C)")
    if forecast.temp_max_c > thresholds.temp_orange_c:
        return ColorDecision(_ORANGE, 90.0, f"heat ({forecast.temp_max_c:.1f}°C)")

    # 4. Neutral default.
    return ColorDecision(_NEUTRAL_WARM_WHITE, 60.0, "no significant weather")


_register_modes()
