#!/usr/bin/env bash
# Rebuild the test pages from index.html, then run the rule checks and a short soak.
# The longer measurements (rates.py, adv.py, catcher_throw.py) are run on their own when tuning.
set -e
cd "$(dirname "$0")"
python3 build_variants.py
python3 scenarios.py
python3 soak.py 3
