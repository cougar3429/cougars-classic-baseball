#!/usr/bin/env bash
# Rebuild the test pages from index.html, then run the rule checks, a short soak, the two-phone rollback check, the online 2-player check
# and the coach selfie check (selfie.py needs network access to cdn.jsdelivr.net).
# The longer measurements (rates.py, adv.py, catcher_throw.py) are run on their own when tuning.
set -e
cd "$(dirname "$0")"
python3 build_variants.py
python3 scenarios.py
python3 soak.py 3
python3 rollback.py 2 8
python3 net.py 15 60
python3 selfie.py
