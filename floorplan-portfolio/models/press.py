"""
models/press.py

The Press dataclass. One instance per press per calendar month.
Immutable — built once by the parser, never modified by calculations.

All field values come directly from the CSV parser.
Calculated values (running speed, ceiling, OEE) live in calculations/.

Period fields (period_start, period_end) enable time-series analysis
across the full 3-year data history.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Press:
    # -- Identity --
    press_id: str                        # e.g. "3450", "3110"
    period_start: date                   # first day of the month this data covers
    period_end: date                     # last day of the month this data covers

    # -- Production --
    net_sheets: int                      # good sheets produced — summed by parser
    gross_sheets: int                    # total sheets including waste — summed by parser
    actual_run_hrs: float                # hours actively running — op code 1020

    # -- Time accounting --
    total_logged_hrs: float              # Auto-Count per-press total — read from CSV col 31
    no_crew_hrs: float                   # hours with no crew scheduled — op code 2060
    planned_maintenance_hrs: float       # scheduled PM hours — op code 2010

    # -- Shifts --
    total_shifts: int                    # number of shifts worked in this period

    # -- Downtime --
    downtime_by_lever: dict              # {"jams": 44.1, "makeready": 94.2, ...}
                                         # keys match LEVERS in config/op_codes.py
    downtime_by_code: dict               # {"2070": {"hours": 12.4, "name": "Jam"}, ...}
                                         # raw per-op-code detail for the deep-dive view
    job_count: int = 0

    def __post_init__(self):
        """Validate that inputs make physical sense. Raises ValueError on bad data."""
        if self.period_end < self.period_start:
            raise ValueError(
                f"[{self.press_id}] period_end ({self.period_end}) "
                f"cannot be before period_start ({self.period_start})"
            )
        if self.net_sheets < 0:
            raise ValueError(f"[{self.press_id}] net_sheets cannot be negative: {self.net_sheets}")
        if self.gross_sheets < self.net_sheets:
            raise ValueError(
                f"[{self.press_id}] gross_sheets ({self.gross_sheets}) "
                f"cannot be less than net_sheets ({self.net_sheets})"
            )
        if self.actual_run_hrs <= 0:
            raise ValueError(f"[{self.press_id}] actual_run_hrs must be > 0: {self.actual_run_hrs}")
        if self.total_logged_hrs <= 0:
            raise ValueError(f"[{self.press_id}] total_logged_hrs must be > 0: {self.total_logged_hrs}")
        if self.no_crew_hrs < 0:
            raise ValueError(f"[{self.press_id}] no_crew_hrs cannot be negative: {self.no_crew_hrs}")
        if self.planned_maintenance_hrs < 0:
            raise ValueError(f"[{self.press_id}] planned_maintenance_hrs cannot be negative")
        if self.total_shifts < 0:
            raise ValueError(f"[{self.press_id}] total_shifts cannot be negative: {self.total_shifts}")

