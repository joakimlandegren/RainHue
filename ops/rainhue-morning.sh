#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/projects/RainHue"
# LAN-only bridge transport; CLI emits this run's verified result, never cached state.
exec .venv/bin/python -m rain_hue morning \
    --local-bridge https://192.168.68.90 --lamp Barnhall --script
