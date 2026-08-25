"""Philips Hue remote (cloud OAuth) client for RainHue v2.

Uses the remote CLIP v2 API at api.meethue.com. Handles OAuth token refresh
via the Hue OAuth2 token endpoint — no hardcoded tokens. When tokens are
refreshed, the new pair is printed to the logs/stdout so it can be written
back to .env (the CLI is stateless; Hue refresh tokens rotate).
"""

import base64
import logging
from dataclasses import dataclass

import requests

from .config import HueConfig

_TOKEN_URL = "https://api.meethue.com/oauth2/token"

logger = logging.getLogger(__name__)


class HueError(RuntimeError):
    """Any failure talking to the Hue remote API."""


@dataclass
class _Tokens:
    access: str
    refresh: str


class HueClient:
    """Minimal remote Hue client: resolve a lamp by name, set its color."""

    def __init__(self, config: HueConfig, timeout: float = 15.0):
        self._cfg = config
        self._timeout = timeout
        self._tokens = _Tokens(config.access_token, config.refresh_token)

    # ── OAuth ────────────────────────────────────────────────────────────────

    def _refresh_tokens(self) -> None:
        """Exchange the refresh token for a new access/refresh pair."""
        if not self._cfg.client_id or not self._cfg.client_secret:
            raise HueError(
                "Hue access token rejected and HUE_CLIENT_ID/HUE_CLIENT_SECRET are not set — "
                "cannot refresh. Run the OAuth pairing flow (see README) and update .env."
            )
        if not self._tokens.refresh:
            raise HueError("No HUE_REFRESH_TOKEN configured — cannot refresh the access token.")

        basic = base64.b64encode(
            f"{self._cfg.client_id}:{self._cfg.client_secret}".encode()
        ).decode()
        try:
            resp = requests.post(
                _TOKEN_URL,
                headers={"Authorization": f"Basic {basic}"},
                data={"grant_type": "refresh_token", "refresh_token": self._tokens.refresh},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise HueError(f"Token refresh request failed: {exc}") from exc

        if resp.status_code != 200:
            raise HueError(f"Token refresh failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        self._tokens = _Tokens(data["access_token"], data.get("refresh_token", self._tokens.refresh))
        # The CLI runs once and exits, so persist-by-print: Joe (or a wrapper)
        # copies these back into .env. Hue rotates refresh tokens, so the old
        # pair is dead after this point.
        logger.warning(
            "Hue tokens refreshed — update .env with the new pair:\n"
            "HUE_TOKEN=%s\nHUE_REFRESH_TOKEN=%s",
            self._tokens.access,
            self._tokens.refresh,
        )

    # ── HTTP plumbing ────────────────────────────────────────────────────────

    def _clip(self, method: str, path: str, body: dict | None = None, retry: bool = True) -> dict:
        """Call the remote CLIP v2 API; refresh the token once on 401."""
        if not self._cfg.username:
            raise HueError("HUE_USERNAME (bridge whitelist user) is not configured.")
        url = f"{self._cfg.base_url}/route/api/{self._cfg.username}{path}"
        headers = {
            "Authorization": f"Bearer {self._tokens.access}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.request(method, url, headers=headers, json=body, timeout=self._timeout)
        except requests.RequestException as exc:
            raise HueError(f"Hue API request failed: {exc}") from exc

        if resp.status_code == 401 and retry:
            logger.info("Hue API returned 401 — refreshing OAuth token and retrying once")
            self._refresh_tokens()
            return self._clip(method, path, body, retry=False)

        if resp.status_code >= 400:
            raise HueError(f"Hue API {method} {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp.json() if resp.text else {}

    # ── Public operations ────────────────────────────────────────────────────

    def list_lights(self) -> list[dict]:
        """Return all lights visible to the bridge user."""
        data = self._clip("GET", "/api/clip/v2/resource/light")
        return data.get("data", [])

    def find_light_id(self, name: str) -> str:
        """Resolve a light name (case-insensitive) to its CLIP v2 id."""
        lights = self.list_lights()
        for light in lights:
            if light.get("metadata", {}).get("name", "").lower() == name.lower():
                return light["id"]
        available = [l.get("metadata", {}).get("name", "?") for l in lights]
        raise HueError(f"Lamp '{name}' not found. Available: {', '.join(available) or '(none)'}")

    def set_color(self, light_id: str, xy: tuple[float, float], brightness: float) -> None:
        """Turn the light on and set xy color + brightness (0-100)."""
        self._clip(
            "PUT",
            f"/api/clip/v2/resource/light/{light_id}",
            {
                "on": {"on": True},
                "color": {"xy": {"x": xy[0], "y": xy[1]}},
                "dimming": {"brightness": max(1.0, min(100.0, brightness))},
            },
        )
        logger.info("Set light %s to xy=%s brightness=%.0f", light_id, xy, brightness)

    def get_light_status(self, light_id: str) -> dict:
        """Read current light state for the status card."""
        data = self._clip("GET", f"/api/clip/v2/resource/light/{light_id}")
        light = (data.get("data") or [{}])[0]
        color = light.get("color", {}).get("xy", {})
        return {
            "name": light.get("metadata", {}).get("name", light_id),
            "on": light.get("on", {}).get("on", False),
            "xy": [color.get("x"), color.get("y")] if color else None,
            "brightness": light.get("dimming", {}).get("brightness"),
        }
