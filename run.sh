#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
unset QT_QPA_PLATFORM_PLUGIN_PATH
unset QT_PLUGIN_PATH
unset QT_QPA_FONTDIR
python3 main.py
