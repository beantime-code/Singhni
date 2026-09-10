#!/usr/bin/env bash
# Render No Place / Part III slides to 1080x1350 PNGs (7 slides).
set -euo pipefail
cd "$(dirname "$0")"
HS=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell
python3 build_carousel_part3.py
mkdir -p out
for i in 01 02 03 04 05 06 07; do
  "$HS" --disable-gpu --no-sandbox --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1080,1350 --screenshot="out/noplace-part3-$i.png" \
    "file://$PWD/slides_part3/slide-$i.html" >/dev/null 2>&1
  echo "rendered slide $i"
done
