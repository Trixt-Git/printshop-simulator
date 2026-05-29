"""
test.py

Locks the verified April 2026 baseline numbers.
Run with: python -m pytest tests/test.py -v

Data source: debug table captured 2026-05-28, April-only load.
Known issue: 2060 Make Ready 2 has one 63hr logging error inflating makeready.
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
    assert _PRESS_BY_ID["2060"].net_sheets  == 215474
    assert _PRESS_BY_ID["2150"].net_sheets  == 1268807
    assert _PRESS_BY_ID["2160"].net_sheets  == 859957
    assert _PRESS_BY_ID["2190"].net_sheets  == 1537245
    assert _PRESS_BY_ID["2330"].net_sheets  == 389954
    assert _PRESS_BY_ID["2500"].net_sheets  == 1044403

def test_available_hours():
    assert round(available_hours(_PRESS_BY_ID["2060"]), 1)  == 247.5
    assert round(available_hours(_PRESS_BY_ID["2150"]), 1)  == 549.2
    assert round(available_hours(_PRESS_BY_ID["2160"]), 1)  == 607.7
    assert round(available_hours(_PRESS_BY_ID["2190"]), 1)  == 492.9
    assert round(available_hours(_PRESS_BY_ID["2330"]), 1)  == 206.4
    assert round(available_hours(_PRESS_BY_ID["2500"]), 1)  == 369.4

def test_running_speed():
    assert round(running_speed_net(_PRESS_BY_ID["2060"]), 1)  == 8165.0
    assert round(running_speed_net(_PRESS_BY_ID["2150"]), 1)  == 7082.8
    assert round(running_speed_net(_PRESS_BY_ID["2160"]), 1)  == 5738.4
    assert round(running_speed_net(_PRESS_BY_ID["2190"]), 1)  == 7914.2
    assert round(running_speed_net(_PRESS_BY_ID["2330"]), 1)  == 5575.6
    assert round(running_speed_net(_PRESS_BY_ID["2500"]), 1)  == 6924.8

def test_total_shifts():
    assert _PRESS_BY_ID["2060"].total_shifts  == 18
    assert _PRESS_BY_ID["2150"].total_shifts  == 48
    assert _PRESS_BY_ID["2160"].total_shifts  == 51
    assert _PRESS_BY_ID["2190"].total_shifts  == 42
    assert _PRESS_BY_ID["2330"].total_shifts  == 19
    assert _PRESS_BY_ID["2500"].total_shifts  == 30


# ---------------------------------------------------------------------------
# Fleet rollup
# ---------------------------------------------------------------------------

def test_fleet_net_sheets():
    summary = summarize_fleet(_PRESSES)
    assert summary.fleet_net_sheets == 5315840

def test_fleet_press_count():
    summary = summarize_fleet(_PRESSES)
    assert summary.press_count == 6

