"""
test.py

Locks the Jan-Jun 2026 averaged baseline numbers from the bundled
demo snapshot (data/snapshot.json — synthetic portfolio data).
Run with: python -m pytest tests/test.py -v
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
    assert _PRESS_BY_ID["3110"].net_sheets  == 255196
    assert _PRESS_BY_ID["3220"].net_sheets  == 1163927
    assert _PRESS_BY_ID["3340"].net_sheets  == 890377
    assert _PRESS_BY_ID["3450"].net_sheets  == 1769543
    assert _PRESS_BY_ID["3560"].net_sheets  == 270822
    assert _PRESS_BY_ID["3670"].net_sheets  == 751435

def test_available_hours():
    assert round(available_hours(_PRESS_BY_ID["3110"]), 1)  == 238.4
    assert round(available_hours(_PRESS_BY_ID["3220"]), 1)  == 530.8
    assert round(available_hours(_PRESS_BY_ID["3340"]), 1)  == 533.2
    assert round(available_hours(_PRESS_BY_ID["3450"]), 1)  == 508.4
    assert round(available_hours(_PRESS_BY_ID["3560"]), 1)  == 141.2
    assert round(available_hours(_PRESS_BY_ID["3670"]), 1)  == 289.4

def test_running_speed():
    assert round(running_speed_net(_PRESS_BY_ID["3110"]), 1)  == 7608.7
    assert round(running_speed_net(_PRESS_BY_ID["3220"]), 1)  == 7010.8
    assert round(running_speed_net(_PRESS_BY_ID["3340"]), 1)  == 5879.0
    assert round(running_speed_net(_PRESS_BY_ID["3450"]), 1)  == 8219.0
    assert round(running_speed_net(_PRESS_BY_ID["3560"]), 1)  == 5650.4
    assert round(running_speed_net(_PRESS_BY_ID["3670"]), 1)  == 6774.0

def test_total_shifts():
    assert _PRESS_BY_ID["3110"].total_shifts  == 23
    assert _PRESS_BY_ID["3220"].total_shifts  == 49
    assert _PRESS_BY_ID["3340"].total_shifts  == 48
    assert _PRESS_BY_ID["3450"].total_shifts  == 46
    assert _PRESS_BY_ID["3560"].total_shifts  == 14
    assert _PRESS_BY_ID["3670"].total_shifts  == 25


# ---------------------------------------------------------------------------
# Fleet rollup
# ---------------------------------------------------------------------------

def test_fleet_net_sheets():
    summary = summarize_fleet(_PRESSES)
    assert summary.fleet_net_sheets == 5101300

def test_fleet_press_count():
    summary = summarize_fleet(_PRESSES)
    assert summary.press_count == 6
