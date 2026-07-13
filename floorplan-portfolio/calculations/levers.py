"""
calculations/levers.py

Lever impact calculations -- the core business logic of FloorPlan.
Answers: if we reduce [category] by [percentage], how many sheets do we gain?

All functions are pure: inputs in, LeverResult out. No side effects.

Note: there is no headroom cap. Lever hours are a percentage of downtime
that already occurred, so recovered hours are physically self-limiting --
you can never recover more hours than were actually lost. An earlier design
included a headroom guardrail; it was removed because the cap can never
trigger (see decisions.md and conversation history).
"""

from dataclasses import dataclass
from models.press import Press
from calculations.baseline import running_speed_net


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LeverResult:
    """
    The complete output of a single lever calculation.
    Everything the UI needs to display the impact of one improvement.
    """
    press_id: str
    lever: str                  # e.g. "jams", "makeready"
    reduction_pct: float        # 0.0 to 1.0 -- e.g. 0.20 for 20%

    hours_available: float      # total hours in this lever category
    hours_recovered: float      # hours recovered = hours_available * reduction_pct

    sheets_gained: int          # good sheets gained from recovered hours
    running_speed: float        # running_speed_net used in calculation
                                # (kept for UI transparency -- explicit higher-up request)


# ---------------------------------------------------------------------------
# Single lever impact
# ---------------------------------------------------------------------------

def lever_impact(press: Press, lever: str, reduction_pct: float) -> LeverResult:
    """
    Calculate the sheet impact of reducing one downtime lever by a percentage.

    Parameters
    ----------
    press : Press
        The press being analyzed.
    lever : str
        Category name -- must match a key in press.downtime_by_lever.
        e.g. "jams", "makeready", "maintenance"
    reduction_pct : float
        Fraction of lever hours to recover. 0.0 to 1.0.
        e.g. 0.20 = recover 20% of jam hours.

    Returns
    -------
    LeverResult
        Full breakdown of impact and sheets gained.

    Raises
    ------
    ValueError
        If lever name not found in press.downtime_by_lever.
    ValueError
        If reduction_pct not between 0 and 1.
    """
    if lever not in press.downtime_by_lever:
        raise ValueError(
            f"[{press.press_id}] Unknown lever: '{lever}'. "
            f"Available: {list(press.downtime_by_lever.keys())}"
        )
    if not 0.0 <= reduction_pct <= 1.0:
        raise ValueError(
            f"reduction_pct must be between 0.0 and 1.0, got {reduction_pct}"
        )

    speed           = running_speed_net(press)
    lever_hrs       = press.downtime_by_lever[lever]
    hours_recovered = lever_hrs * reduction_pct
    sheets_gained   = int(hours_recovered * speed)

    return LeverResult(
        press_id        = press.press_id,
        lever           = lever,
        reduction_pct   = reduction_pct,
        hours_available = lever_hrs,
        hours_recovered = round(hours_recovered, 2),
        sheets_gained   = sheets_gained,
        running_speed   = round(speed, 1),
    )


# ---------------------------------------------------------------------------
# Fleet rollup
# ---------------------------------------------------------------------------

def fleet_lever_impact(presses: list[Press], lever: str, reduction_pct: float) -> dict:
    """
    Calculate lever impact across the entire fleet.
    Each press calculated independently.

    Returns a summary dict:
    {
        "lever": str,
        "reduction_pct": float,
        "total_sheets_gained": int,
        "total_hours_recovered": float,
        "by_press": list[LeverResult],
    }
    """
    results = [
        lever_impact(press, lever, reduction_pct)
        for press in presses
        if lever in press.downtime_by_lever
    ]

    return {
        "lever":                 lever,
        "reduction_pct":         reduction_pct,
        "total_sheets_gained":   sum(r.sheets_gained for r in results),
        "total_hours_recovered": round(sum(r.hours_recovered for r in results), 2),
        "by_press":              results,
    }


# ---------------------------------------------------------------------------
# Rank levers by impact
# ---------------------------------------------------------------------------

def rank_levers(press: Press, reduction_pct: float = 0.20) -> list[LeverResult]:
    """
    Calculate impact for every lever on a press at a given reduction percentage.
    Returns results sorted by sheets_gained descending -- biggest opportunity first.

    Default 20% reduction matches the 'Path to Target' view assumption.
    """
    results = [
        lever_impact(press, lever, reduction_pct)
        for lever in press.downtime_by_lever
        if press.downtime_by_lever[lever] > 0  # skip levers with no hours
    ]
    return sorted(results, key=lambda r: r.sheets_gained, reverse=True)
