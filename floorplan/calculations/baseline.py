""".
calculations/baseline.py

Baseline calculations — the foundation everything else builds on.
All functions are pure: Press in, number out. No side effects.

Math is locked per floorplan_calculations.md and decisions.md.
Do not change formulas without updating the spec first.

Functions:
    running_speed_net(press)  → net sheets per actual run hour (used in ALL lever math)
    available_hours(press)    → hours the press could have been productive
    ceiling_sheets(press)     → max sheets achievable at current running speed
    oee_availability(press)   → fraction of available hours spent running (diagnostic)
    oee_quality(press)        → fraction of gross sheets that were good (diagnostic)

Note (decision D5): OEE Performance and a combined "overall OEE" score were
removed. The 15-year-old fleet has no meaningful manufacturer rated speed to
measure performance against. running_speed_net IS the real measured speed --
there is no theoretical target left to compare it to. Availability and Quality
remain as standalone diagnostics because they compare against real measured
quantities (available hours, gross sheets), not a manufacturer spec.
"""

from models.press import Press


# ---------------------------------------------------------------------------
# Running speed
# ---------------------------------------------------------------------------

def running_speed_net(press: Press) -> float:
    """
    Net sheets produced per actual run hour.
    The press's real-world productive speed -- used in ALL lever math.

    Formula: net_sheets / actual_run_hrs

    This is a measured fact, not a target. It already has everything baked in:
    operator pace, substrate, ink, press age. It is the all-in blended average
    of what the press actually did.
    """
    return press.net_sheets / press.actual_run_hrs


# ---------------------------------------------------------------------------
# Time accounting
# ---------------------------------------------------------------------------

def available_hours(press: Press) -> float:
    """
    Hours the press could have been productively running.
    Removes time that was never available to begin with.

    Formula: total_logged_hrs - no_crew_hrs - planned_maintenance_hrs

    Why subtract these two:
    - no_crew_hrs (2060): no one was scheduled. Can't run without crew.
    - planned_maintenance_hrs (2010): committed maintenance window.
      We chose to take the press down -- it wasn't a loss, it was a plan.

    What's left is the time we had to work with. Ceiling and lever impacts
    are all calculated against this number.
    """
    return (
        press.total_logged_hrs
        - press.no_crew_hrs
        - press.planned_maintenance_hrs
    )


# ---------------------------------------------------------------------------
# Ceiling
# ---------------------------------------------------------------------------

def ceiling_sheets(press: Press) -> int:
    """
    Maximum sheets achievable in available hours at current running speed.
    A realistic ceiling -- not a theoretical maximum.

    Formula: available_hours * running_speed_net

    Uses running_speed_net (measured reality) rather than any theoretical
    speed, so the ceiling is grounded in what the press has actually
    demonstrated it can do.
    """
    return int(available_hours(press) * running_speed_net(press))


# ---------------------------------------------------------------------------
# Diagnostics -- not used in lever math
# ---------------------------------------------------------------------------

def oee_availability(press: Press) -> float:
    """
    Availability: fraction of available hours spent actually running.
    Diagnostic only -- shows where time went, not used in lever calculations.

    Formula: actual_run_hrs / available_hours
    Returns a ratio between 0 and 1 (multiply by 100 for percentage).
    """
    avail = available_hours(press)
    if avail <= 0:
        return 0.0
    return press.actual_run_hrs / avail


def oee_quality(press: Press) -> float:
    """
    Quality: fraction of gross sheets that were good (net) sheets.
    Diagnostic only.

    Formula: net_sheets / gross_sheets
    Returns a ratio between 0 and 1.
    """
    if press.gross_sheets <= 0:
        return 0.0
    return press.net_sheets / press.gross_sheets
