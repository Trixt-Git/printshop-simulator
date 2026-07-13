"""
test.py

Locks the verified baseline numbers for the bundled snapshot
(six presses averaged across the 2026_01–2026_06 periods).
Run with: python -m pytest tests/test.py -v

Known issue: 4080 Make Ready 2 has one ~60hr logging error inflating makeready.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from floorplan_calculator import _PRESS_BY_ID, _PRESSES
from calculations.baseline import (
    running_speed_net,
    available_hours,
)
from calculations.fleet import summarize_fleet


# ---------------------------------------------------------------------------
# Per-press baseline
# ---------------------------------------------------------------------------

def test_net_sheets():
    assert _PRESS_BY_ID["4080"].net_sheets  == 269922
    assert _PRESS_BY_ID["4140"].net_sheets  == 1124950
    assert _PRESS_BY_ID["4180"].net_sheets  == 925569
    assert _PRESS_BY_ID["4210"].net_sheets  == 1746177
    assert _PRESS_BY_ID["4360"].net_sheets  == 264216
    assert _PRESS_BY_ID["4520"].net_sheets  == 862252

def test_available_hours():
    assert round(available_hours(_PRESS_BY_ID["4080"]), 1)  == 224.1
    assert round(available_hours(_PRESS_BY_ID["4140"]), 1)  == 579.6
    assert round(available_hours(_PRESS_BY_ID["4180"]), 1)  == 558.9
    assert round(available_hours(_PRESS_BY_ID["4210"]), 1)  == 461.9
    assert round(available_hours(_PRESS_BY_ID["4360"]), 1)  == 148.6
    assert round(available_hours(_PRESS_BY_ID["4520"]), 1)  == 278.9

def test_running_speed():
    assert round(running_speed_net(_PRESS_BY_ID["4080"]), 1)  == 8277.3
    assert round(running_speed_net(_PRESS_BY_ID["4140"]), 1)  == 6360.3
    assert round(running_speed_net(_PRESS_BY_ID["4180"]), 1)  == 5962.9
    assert round(running_speed_net(_PRESS_BY_ID["4210"]), 1)  == 8951.5
    assert round(running_speed_net(_PRESS_BY_ID["4360"]), 1)  == 5270.6
    assert round(running_speed_net(_PRESS_BY_ID["4520"]), 1)  == 7828.0

def test_total_shifts():
    assert _PRESS_BY_ID["4080"].total_shifts  == 22
    assert _PRESS_BY_ID["4140"].total_shifts  == 54
    assert _PRESS_BY_ID["4180"].total_shifts  == 52
    assert _PRESS_BY_ID["4210"].total_shifts  == 41
    assert _PRESS_BY_ID["4360"].total_shifts  == 14
    assert _PRESS_BY_ID["4520"].total_shifts  == 24


# ---------------------------------------------------------------------------
# Fleet rollup
# ---------------------------------------------------------------------------

def test_fleet_net_sheets():
    summary = summarize_fleet(_PRESSES)
    assert summary.fleet_net_sheets == 5193086

def test_fleet_press_count():
    summary = summarize_fleet(_PRESSES)
    assert summary.press_count == 6
