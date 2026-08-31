"""HTTP API + single-page web UI for RainHue v2.

LAN-only by design (no auth layer — Joe's scope). Serves:
  GET  /                single-page UI
  GET  /weather         condensed 12h forecast
  POST /set-color       one weather->color cycle (legacy trigger)
  GET  /api/status      lamp state + last decision seen by this process
  POST /api/mode/<name> apply a manual color mode (rain/snow/heat/extreme/neutral)
  POST /api/morning     run the morning logic now
"""

import logging

from flask import Flask, jsonify, request

from .colors import MODES, ColorDecision
from .config import load
from .core import run_once, serialize_decision
from .hue import HueClient, HueError
from .state import read_state, write_state
from .weather import fetch_forecast

logger = logging.getLogger(__name__)


def create_app(hue_client=None):
    """App factory. hue_client is injectable for tests.

    Last decision is shared across processes via the state file
    (see state.py): cron CLI runs and API triggers both write it; the status
    endpoint reads it as the source of truth, falling back to this process's
    in-memory record if the file is missing or corrupt.
    """
    app = Flask(__name__)
    app.config["rain_hue_config"] = load()
    app.config["rain_hue_hue_client"] = hue_client
    app.config["rain_hue_last_decision"] = None

    def _hue():
        if app.config["rain_hue_hue_client"] is None:
            app.config["rain_hue_hue_client"] = HueClient(app.config["rain_hue_config"].hue)
        return app.config["rain_hue_hue_client"]

    def _lamp_name() -> str:
        return app.config["rain_hue_config"].hue.default_lamp

    def _record_decision(decision: ColorDecision, lamp: str, forecast=None) -> dict:
        record = serialize_decision(decision, lamp, forecast)
        app.config["rain_hue_last_decision"] = record
        write_state(record)
        return record

    def _last_decision() -> dict | None:
        return read_state() or app.config["rain_hue_last_decision"]

    # ── Page ─────────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        return _INDEX_HTML

    # ── Error shape: API consumers always get JSON, never the HTML 500 page ──

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        return e

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("unhandled error on %s", request.path)
        if request.path.startswith("/api/") or request.path == "/set-color":
            return jsonify({"error": "Internal server error"}), 500
        return e

    # ── Data endpoints ───────────────────────────────────────────────────────

    @app.get("/api/status")
    def status():
        """Lamp live state + last decision seen by this process."""
        lamp = _lamp_name()
        light = {"name": lamp, "on": None, "xy": None, "brightness": None}
        light_error = None
        try:
            light = _hue().get_light_status(_hue().find_light_id(lamp))
        except (HueError, RuntimeError) as exc:
            light_error = str(exc)
            logger.warning("status: could not read lamp state: %s", exc)
        return jsonify(
            {
                "lamp": light,
                "lamp_error": light_error,
                "last_decision": _last_decision(),
                "modes": sorted(MODES.keys()),
            }
        )

    @app.post("/api/mode/<name>")
    def set_mode(name: str):
        """Apply a manual color mode to the lamp."""
        decision = MODES.get(name)
        if decision is None:
            return jsonify({"error": f"Unknown mode '{name}'", "modes": sorted(MODES.keys())}), 404
        lamp = request.args.get("lamp") or _lamp_name()
        try:
            light_id = _hue().find_light_id(lamp)
            _hue().set_color(light_id, decision.xy, decision.brightness)
        except (HueError, RuntimeError) as exc:
            logger.exception("mode '%s' failed", name)
            return jsonify({"error": str(exc)}), 502
        return jsonify(_record_decision(decision, lamp))

    @app.post("/api/morning")
    def morning():
        """Run the morning logic now (weather -> color)."""
        lamp = request.args.get("lamp") or _lamp_name()
        try:
            result = run_once(
                app.config["rain_hue_config"], lamp=lamp, hue_client=_hue()
            )
        except RuntimeError as exc:
            logger.exception("morning run failed")
            return jsonify({"error": str(exc)}), 502
        # run_once already wrote the state file; update the in-memory copy too.
        record = serialize_decision(result.decision, result.lamp, result.forecast)
        app.config["rain_hue_last_decision"] = record
        return jsonify(record)

    # ── Legacy endpoints (kept from v2 core) ─────────────────────────────────

    @app.post("/set-color")
    def set_color():
        config = app.config["rain_hue_config"]
        lamp = request.args.get("lamp")
        try:
            result = run_once(config, lamp=lamp, hue_client=_hue())
        except RuntimeError as exc:
            logger.exception("set-color failed")
            return jsonify({"error": str(exc)}), 502
        record = serialize_decision(result.decision, result.lamp, result.forecast)
        app.config["rain_hue_last_decision"] = record
        return jsonify(record)

    @app.get("/weather")
    def weather():
        config = app.config["rain_hue_config"]
        try:
            f = fetch_forecast(config.latitude, config.longitude, config.timezone, config.forecast_hours)
        except RuntimeError as exc:
            logger.exception("weather fetch failed")
            return jsonify({"error": str(exc)}), 502
        return jsonify(
            {
                "total_precip_mm": f.total_precip_mm,
                "total_snowfall_cm": f.total_snowfall_cm,
                "max_precip_probability": f.max_precip_probability,
                "temp_max_c": f.temp_max_c,
            }
        )

    return app


_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RainHue</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 min-h-screen font-sans">
  <main class="max-w-md mx-auto px-4 py-8">
    <header class="flex items-center gap-3 mb-6">
      <div class="w-10 h-10 rounded-xl bg-sky-500 flex items-center justify-center text-white text-xl">☔</div>
      <h1 class="text-2xl font-extrabold text-slate-800">RainHue</h1>
    </header>

    <!-- Status card -->
    <section class="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
      <h2 class="text-xs font-bold uppercase tracking-wide text-slate-400 mb-3">Lamp status</h2>
      <div class="flex items-center gap-4">
        <div id="swatch" class="w-14 h-14 rounded-xl border border-slate-200 bg-slate-100 flex-shrink-0"></div>
        <div class="min-w-0">
          <p id="lamp-name" class="font-bold text-slate-800 truncate">—</p>
          <p id="lamp-state" class="text-sm text-slate-500">loading…</p>
          <p id="lamp-error" class="text-xs text-amber-600 mt-1 hidden"></p>
        </div>
      </div>
    </section>

    <!-- Last decision card -->
    <section class="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 mb-4">
      <h2 class="text-xs font-bold uppercase tracking-wide text-slate-400 mb-3">Last decision</h2>
      <div id="decision-empty" class="text-sm text-slate-400 italic">No decision yet in this session.</div>
      <div id="decision" class="hidden">
        <p id="decision-reason" class="font-semibold text-slate-800"></p>
        <p id="decision-meta" class="text-sm text-slate-500 mt-0.5"></p>
        <div id="decision-forecast" class="text-xs text-slate-400 mt-2"></div>
      </div>
    </section>

    <!-- Mode buttons -->
    <section class="bg-white rounded-2xl shadow-sm border border-slate-200 p-5">
      <h2 class="text-xs font-bold uppercase tracking-wide text-slate-400 mb-3">Set mode</h2>
      <div class="grid grid-cols-2 gap-2 mb-3" id="modes"></div>
      <button id="morning"
        class="w-full py-2.5 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 text-white font-bold rounded-xl transition-colors text-sm">
        ▶ Run morning logic now
      </button>
      <p id="action-msg" class="text-xs text-center mt-2 h-4"></p>
    </section>
  </main>

<script>
const xyToRgb = (x, y, bri = 1.0) => {
  // CIE xy -> sRGB approx (Hue-style gamma)
  const z = 1.0 - x - y;
  const Y = bri, X = (Y / y) * x, Z = (Y / y) * z;
  let r =  X * 1.656492 - Y * 0.354851 - Z * 0.255038;
  let g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152;
  let b =  X * 0.051713 - Y * 0.121364 + Z * 1.011530;
  const gamma = v => v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1/2.4) - 0.055;
  r = Math.min(1, Math.max(0, gamma(r)));
  g = Math.min(1, Math.max(0, gamma(g)));
  b = Math.min(1, Math.max(0, gamma(b)));
  return `rgb(${r*255|0}, ${g*255|0}, ${b*255|0})`;
};

const MODE_STYLE = {
  rain:    'bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-200',
  snow:    'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200',
  freezing:'bg-cyan-50 text-cyan-800 border-cyan-200 hover:bg-cyan-100',
  heat:    'bg-orange-100 text-orange-800 border-orange-200 hover:bg-orange-200',
  extreme: 'bg-red-100 text-red-800 border-red-200 hover:bg-red-200',
  neutral: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100',
};
const MODE_LABEL = { rain: '🌧 Rain', snow: '❄ Snow', freezing: '🥶 Freezing', heat: '🌤 Heat', extreme: '🔥 Extreme', neutral: '💡 Neutral' };

async function fetchJson(url, options = {}) {
  // Robust fetch: never let a non-JSON body (e.g. an HTML 500 page) surface
  // as a raw "Unexpected token <" parse error — turn it into a readable one.
  const resp = await fetch(url, options);
  const contentType = resp.headers.get('content-type') || '';
  let body = null;
  if (contentType.includes('application/json')) {
    body = await resp.json();
  } else {
    const text = await resp.text();
    if (!resp.ok) {
      throw new Error('Server error ' + resp.status + (text ? ' — the endpoint did not return JSON' : ''));
    }
    throw new Error('Unexpected response from server (not JSON)');
  }
  if (!resp.ok) {
    throw new Error((body && body.error) || ('Server error ' + resp.status));
  }
  return body;
}

async function refresh() {
  try {
    const s = await fetchJson('/api/status');
    document.getElementById('lamp-name').textContent = s.lamp.name || '—';
    if (s.lamp_error) {
      document.getElementById('lamp-state').textContent = 'unreachable';
      const e = document.getElementById('lamp-error');
      e.textContent = s.lamp_error;
      e.classList.remove('hidden');
    } else {
      document.getElementById('lamp-state').textContent =
        (s.lamp.on ? 'On' : 'Off') + (s.lamp.brightness != null ? ' · ' + Math.round(s.lamp.brightness) + '%' : '');
      if (s.lamp.xy) {
        document.getElementById('swatch').style.background =
          xyToRgb(s.lamp.xy[0], s.lamp.xy[1], (s.lamp.brightness || 50) / 100);
      }
    }
    const d = s.last_decision;
    if (d) {
      document.getElementById('decision-empty').classList.add('hidden');
      document.getElementById('decision').classList.remove('hidden');
      document.getElementById('decision-reason').textContent = d.reason;
      document.getElementById('decision-meta').textContent =
        d.lamp + ' · ' + new Date(d.at).toLocaleString();
      if (d.forecast) {
        document.getElementById('decision-forecast').textContent =
          `Precip ${d.forecast.total_precip_mm}mm · Snow ${d.forecast.total_snowfall_cm}cm · ` +
          `Prob ${d.forecast.max_precip_probability}% · Max ${d.forecast.temp_max_c}°C`;
      }
    }
    if (!document.getElementById('modes').hasChildNodes()) {
      for (const m of s.modes) {
        const btn = document.createElement('button');
        btn.textContent = MODE_LABEL[m] || m;
        btn.className = 'py-2.5 rounded-xl border text-sm font-semibold transition-colors ' + (MODE_STYLE[m] || '');
        btn.onclick = () => act('/api/mode/' + m, btn, (MODE_LABEL[m] || m));
        document.getElementById('modes').appendChild(btn);
      }
    }
  } catch (e) {
    document.getElementById('lamp-state').textContent = 'status unavailable';
  }
}

async function act(url, btn, label) {
  const msg = document.getElementById('action-msg');
  msg.textContent = 'working…';
  msg.className = 'text-xs text-center mt-2 h-4 text-slate-500';
  if (btn) btn.disabled = true;
  try {
    const body = await fetchJson(url, { method: 'POST' });
    msg.textContent = '✓ ' + body.reason;
    msg.className = 'text-xs text-center mt-2 h-4 text-emerald-600';
    refresh();
  } catch (e) {
    msg.textContent = '✗ ' + label + ' failed: ' + e.message;
    msg.className = 'text-xs text-center mt-2 h-4 text-red-600';
  } finally {
    if (btn) btn.disabled = false;
  }
}

document.getElementById('morning').onclick = (e) => act('/api/morning', e.target, 'Morning logic');
refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="0.0.0.0", port=5000)
