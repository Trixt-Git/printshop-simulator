"""
calculations/planner.py

Scenario planner — takes a user-defined improvement plan and calculates
progress toward a sheet target.

A plan is a dict of lever → reduction percentage:
    {"jams": 0.20, "makeready": 0.15, "maintenance": 0.10}

The planner runs lever_impact for every press × lever combination,
rolls up the total sheets recovered, and compares against the target.

Default target: current fleet sheets × 1.10 (10% stretch goal).
User can override with any target they choose.
"""

from dataclasses import dataclass
from models.press import Press
from calculations.levers import lever_impact, LeverResult


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanResult:
    """
    Complete output of a scenario plan.
    Everything the UI needs to show progress toward target.
    """
    # -- Sheets --
    current_sheets: int         # actual fleet output this period
    target_sheets: int          # goal (default: current * 1.10, user overridable)
    sheets_recovered: int       # additional sheets the plan would produce
    projected_sheets: int       # current + recovered

    # -- Gap tracking --
    gap_to_target: int          # target - current (how far we started from goal)
    gap_remaining: int          # target - projected (how far we still need to go)
    pct_of_gap_closed: float    # sheets_recovered / gap_to_target (0.0 to 1.0+)

    # -- Status --
    on_target: bool             # True if projected >= target

    # -- Breakdown --
    plan: dict                  # the user's input {"jams": 0.20, ...}
    lever_results: list         # list of LeverResult — full press x lever breakdown


# ---------------------------------------------------------------------------
# Core planner function
# ---------------------------------------------------------------------------

def build_plan(
    presses: list[Press],
    plan: dict,
    target_sheets: int = None,
) -> PlanResult:
    """
    Calculate the impact of a multi-lever improvement plan across the fleet.

    Parameters
    ----------
    presses : list[Press]
        The full fleet for the period being analyzed.
    plan : dict
        Lever reductions the user wants to model.
        Keys must match lever names in LEVERS config.
        Values are floats between 0.0 and 1.0.
        Example: {"jams": 0.20, "makeready": 0.15}
    target_sheets : int, optional
        Goal in net sheets. Defaults to current fleet sheets * 1.10.

    Returns
    -------
    PlanResult
        Full breakdown of current state, plan impact, and gap to target.
    """
    if not presses:
        raise ValueError("build_plan called with an empty press list")

    # Validate every lever name in the plan against the known lever set.
    # Fail loud -- a typo'd lever name must never silently produce zero impact.
    known_levers = set()
    for p in presses:
        known_levers.update(p.downtime_by_lever.keys())
    for lever in plan:
        if lever not in known_levers:
            raise ValueError(
                f"Unknown lever in plan: '{lever}'. "
                f"Known levers: {sorted(known_levers)}"
            )

    # Current fleet output
    current_sheets = sum(p.net_sheets for p in presses)

    # Default target -- 10% stretch goal
    if target_sheets is None:
        target_sheets = int(current_sheets * 1.10)

    # Run lever_impact for every press x lever combination.
    # A press may legitimately have 0 hours in a lever -- skip those
    # (no impact) but the lever name itself is already validated above.
    lever_results = []
    for press in presses:
        for lever, reduction_pct in plan.items():
            if press.downtime_by_lever.get(lever, 0) <= 0:
                continue
            result = lever_impact(press, lever, reduction_pct)
            lever_results.append(result)

    # Roll up total sheets recovered
    sheets_recovered = sum(r.sheets_gained for r in lever_results)
    projected_sheets = current_sheets + sheets_recovered

    # Gap math
    gap_to_target = target_sheets - current_sheets
    gap_remaining = target_sheets - projected_sheets

    # What fraction of the gap does this plan close?
    if gap_to_target <= 0:
        pct_of_gap_closed = 1.0   # already at or above target
    else:
        pct_of_gap_closed = sheets_recovered / gap_to_target

    return PlanResult(
        current_sheets    = current_sheets,
        target_sheets     = target_sheets,
        sheets_recovered  = sheets_recovered,
        projected_sheets  = projected_sheets,
        gap_to_target     = gap_to_target,
        gap_remaining     = gap_remaining,
        pct_of_gap_closed = round(pct_of_gap_closed, 4),
        on_target         = projected_sheets >= target_sheets,
        plan              = plan,
        lever_results     = lever_results,
    )


# ---------------------------------------------------------------------------
# Convenience — what reduction % is needed to hit target with one lever?
# ---------------------------------------------------------------------------

def required_reduction(
    presses: list[Press],
    lever: str,
    target_sheets: int = None,
) -> float:
    """
    Given a single lever applied fleet-wide, what reduction percentage
    is needed to close the entire gap to target?

    Returns a float 0.0 to 1.0, or None if the lever can't close the gap
    even at 100% reduction.

    Useful for answering: "if we only fixed makeready, how much would we
    need to improve to hit our goal?"
    """
    current_sheets = sum(p.net_sheets for p in presses)

    if target_sheets is None:
        target_sheets = int(current_sheets * 1.10)

    gap = target_sheets - current_sheets
    if gap <= 0:
        return 0.0

    # Calculate max sheets available from this lever at 100%
    max_result = build_plan(presses, {lever: 1.0}, target_sheets)
    max_sheets = max_result.sheets_recovered

    if max_sheets <= 0:
        return None  # lever has no hours, can't help

    required = gap / max_sheets

    if required > 1.0:
        return None  # even 100% reduction isn't enough

    return round(required, 4)
