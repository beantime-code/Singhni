#!/usr/bin/env bash
# Render No Place / Part II slides to 1080x1350 PNGs.
# Uses headless_shell: chrome --headless reports a 1263px viewport for a
# requested 1350, which shifts bottom-anchored elements. headless_shell does not.
set -euo pipefail
cd "$(dirname "$0")"
HS=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
python3 build_carousel.py
mkdir -p out
for i in 01 02 03 04 05 06; do
  "$HS" --disable-gpu --no-sandbox --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1080,1350 --screenshot="out/noplace-part2-$i.png" \
    "file://$PWD/slides/slide-$i.html" >/dev/null 2>&1
  echo "rendered slide $i"
done
