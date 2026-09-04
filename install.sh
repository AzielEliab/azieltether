#!/usr/bin/env bash
# AzielTether local install from this tree (not the counted Worker /install.sh).
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
echo
echo "Installed AzielTether 0.1.0."
echo "Run: azieltether doctor"
echo "Then: azieltether serve"
echo "Open http://127.0.0.1:19740 (this computer only)"
echo "Author: Aziel Eliab."
