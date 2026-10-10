#!/bin/bash
# Double-click to start Ishpreet Studio. It opens in your browser; close this window to quit.
cd "$(dirname "$0")/tools" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is missing. macOS will offer to install the Command Line Tools: accept, then double-click again."
  xcode-select --install 2>/dev/null
  read -r -p "Press Enter to close."
  exit 1
fi
python3 ishpreet_studio.py
status=$?
if [ $status -ne 0 ]; then
  echo
  echo "Ishpreet Studio stopped with an error (code $status). The message above says why; it is also in studio_log.txt."
  read -r -p "Press Enter to close."
fi
