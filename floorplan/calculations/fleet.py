"""
calculations/fleet.py

Fleet-wide rollups -- the "do this for all presses" layer.

Every function in baseline.py and levers.py operates on one press.
This file aggregates those single-press results into fleet totals
for the top-level dashboard view.

All functions are pure: list[Press] in, FleetSummary or list out.

Key correctness note: fleet ratios (availability, quality) are weighted --
they sum the raw hours/sheets first, then divide. They are NOT the average
of per-press percentages. Averaging percentages would let a tiny press
distort the fleet number; a press running 40 hours should not move the
fleet ratio as much as one running 900 hours.
"""

from dataclasses import dataclass
from models.press import Press
from calculations.baseline import (
    running_speed_net,
    available_hours,
    ceiling_sheets,
)


# ---------------------------------------------------------------------------
# Per-press summary -- one row of the fleet breakdown
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PressSummary:
    """
    One press's headline numbers. The per-press rows that sit
    underneath the fleet totals on the dashboard.
    """
    press_id: str
    net_sheets: int
    gross_sheets: int
    actual_run_hrs: float
    available_hrs: float
    running_speed: float        # running_speed_net
    ceiling_sheets: int
    opportunity_sheets: int     # ceiling - net
    availability: float         # run_hrs / available_hrs (0.0-1.0)
    quality: float              # net / gross (0.0-1.0)
    total_shifts: int


# ---------------------------------------------------------------------------
# Fleet summary -- the top-level dashboard numbers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FleetSummary:
    """
    Fleet-wide totals plus the per-press breakdown.
    Everything the top-level dashboard view needs in one object.
    """
    # -- Fleet totals --
    fleet_net_sheets: int
    fleet_gross_sheets: int
    fleet_ceiling: int
    fleet_opportunity: int          # total recoverable sheets fleet-wide

    # -- Fleet weighted ratios --
    fleet_availability: float       # Σ run hrs / Σ available hrs
    fleet_quality: float            # Σ net / Σ gross

    # -- Fleet hours --
    fleet_run_hrs: float
    fleet_available_hrs: float

    # -- Counts --
    press_count: int
    fleet_total_shifts: int

    # -- Breakdown --
    by_press: list                  # list[PressSummary], sorted by press_id


# ---------------------------------------------------------------------------
# Per-press summary builder
# ---------------------------------------------------------------------------

def summarize_press(press: Press) -> PressSummary:
    """
    Build a PressSummary -- one press's headline numbers.
    Pure: composes the baseline functions, stores nothing.
    """
    avail   = available_hours(press)
    speed   = running_speed_net(press)
    ceiling = ceiling_sheets(press)

    # Availability -- guard against zero available hours
    availability = press.actual_run_hrs / avail if avail > 0 else 0.0

    # Quality -- guard against zero gross
    quality = press.net_sheets / press.gross_sheets if press.gross_sheets > 0 else 0.0

    return PressSummary(
        press_id           = press.press_id,
        net_sheets         = press.net_sheets,
        gross_sheets       = press.gross_sheets,
        actual_run_hrs     = round(press.actual_run_hrs, 2),
        available_hrs      = round(avail, 2),
        running_speed      = round(speed, 1),
        ceiling_sheets     = ceiling,
        opportunity_sheets = ceiling - press.net_sheets,
        availability       = round(availability, 4),
        quality            = round(quality, 4),
        total_shifts       = press.total_shifts,
    )


# ---------------------------------------------------------------------------
# Fleet summary builder
# ---------------------------------------------------------------------------

def summarize_fleet(presses: list[Press]) -> FleetSummary:
    """
    Build a FleetSummary -- fleet totals plus per-press breakdown.

    Fleet ratios are weighted: raw hours and sheets are summed first,
    then divided. This is NOT the mean of per-press percentages.

    Raises
    ------
    ValueError
        If presses is empty -- there is no fleet to summarize.
    """
    if not presses:
        raise ValueError("summarize_fleet called with an empty press list")

    # Per-press summaries first
    summaries = [summarize_press(p) for p in presses]
    summaries.sort(key=lambda s: s.press_id)

    # Sum raw quantities for weighted ratios
    fleet_net       = sum(p.net_sheets for p in presses)
    fleet_gross     = sum(p.gross_sheets for p in presses)
    fleet_run_hrs   = sum(p.actual_run_hrs for p in presses)
    fleet_avail_hrs = sum(available_hours(p) for p in presses)
    fleet_ceiling   = sum(s.ceiling_sheets for s in summaries)
    fleet_shifts    = sum(p.total_shifts for p in presses)

    # Weighted fleet ratios -- guard against zero denominators
    fleet_availability = fleet_run_hrs / fleet_avail_hrs if fleet_avail_hrs > 0 else 0.0
    fleet_quality      = fleet_net / fleet_gross if fleet_gross > 0 else 0.0

    return FleetSummary(
        fleet_net_sheets    = fleet_net,
        fleet_gross_sheets  = fleet_gross,
        fleet_ceiling       = fleet_ceiling,
        fleet_opportunity   = fleet_ceiling - fleet_net,
        fleet_availability  = round(fleet_availability, 4),
        fleet_quality       = round(fleet_quality, 4),
        fleet_run_hrs       = round(fleet_run_hrs, 2),
        fleet_available_hrs = round(fleet_avail_hrs, 2),
        press_count         = len(presses),
        fleet_total_shifts  = fleet_shifts,
        by_press            = summaries,
    )


# ---------------------------------------------------------------------------
# Weak link -- which press has the most recoverable opportunity
# ---------------------------------------------------------------------------

def weakest_press(presses: list[Press]) -> PressSummary:
    """
    Return the PressSummary with the largest opportunity_sheets --
    the press where improvement would recover the most output.

    Raises
    ------
    ValueError
        If presses is empty.
    """
    if not presses:
        raise ValueError("weakest_press called with an empty press list")

    summaries = [summarize_press(p) for p in presses]
    return max(summaries, key=lambda s: s.opportunity_sheets)
