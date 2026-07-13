"""
parsers/productivity_csv.py

Reads the 'Productivity by Machine' CSV export from Auto-Count.
Returns one Press object per machine.

Key behaviors:
- Deduplicates rows by (machine, op_code, op_name, time) before processing
- Parses HH:MM:SS time strings into float hours
- Routes each row to: run hours, a lever bucket, or an exclusion bucket
- Reads per-press total logged hours from col 31 (read once per press)
- Shift counts pulled from a separate Machine Log CSV via parse_shifts()
"""

import csv
import calendar
import re
from datetime import date
from pathlib import Path
from parsers.base import ProductivityParser
from models.press import Press
from config.op_codes import (
    LEVER_CODE_TO_CATEGORY,
    LEVERS,
    PRODUCTIVE,
    EXCLUDED,
    MACHINE_MAP,
)


def _parse_period_from_filename(path: Path) -> tuple[date, date]:
    """
    Extract period_start and period_end from a filename like:
        productivity_2026_01.csv  ->  date(2026, 1, 1), date(2026, 1, 31)

    Raises ValueError if the filename doesn't match the expected pattern.
    """
    match = re.search(r"(\d{4})_(\d{2})", path.stem)
    if not match:
        raise ValueError(
            f"Cannot parse period from filename: '{path.name}'\n"
            f"Expected format: productivity_YYYY_MM.csv (e.g. productivity_2026_01.csv)"
        )
    year  = int(match.group(1))
    month = int(match.group(2))
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _parse_hms(time_str: str) -> float:
    """
    Convert 'HH:MM:SS' string to float hours.
    Returns 0.0 if the string is empty or malformed.

    Examples:
        '1:30:00' → 1.5
        '0:45:00' → 0.75
        ''        → 0.0
    """
    if not time_str or not time_str.strip():
        return 0.0
    try:
        parts = time_str.strip().split(":")
        hours   = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours + minutes / 60 + seconds / 3600
    except (ValueError, IndexError):
        return 0.0


def _safe_int(value: str) -> int:
    """Parse a sheet count string to int. Returns 0 on empty or bad input."""
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


class ProductivityCSVParser(ProductivityParser):
    """
    Parses the Auto-Count 'Productivity by Machine' CSV export.
    Column indices verified against real CSV (May 2026) — see constants below.
    """

    # Column indices (0-based) — verified against real CSV May 2026
    COL_MACHINE    = 18
    COL_OP_CODE    = 20
    COL_OP_NAME    = 21
    COL_TIME       = 23
    COL_GROSS      = 25
    COL_NET        = 27
    COL_TOTAL_TIME = 31

    def parse(self, source, machine_log=None) -> list[Press]:
        """
        Parse a Productivity by Machine CSV and return one Press per machine.

        Parameters
        ----------
        source : str or Path
            Path to the Productivity by Machine CSV.
        machine_log : str or Path, optional
            Path to the Machine Log CSV for shift counting.
            If not provided, total_shifts will be 0 on all Press objects.

        Returns
        -------
        list[Press]
            One fully-populated Press per recognized machine.
        """
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"CSV not found: {source}")

        period_start, period_end = _parse_period_from_filename(source)
        raw_rows   = self._read_and_deduplicate(source)
        press_data = self._aggregate(raw_rows)
        shift_counts, job_counts = self.parse_shifts(machine_log) if machine_log else ({},{})
        return self._build_presses(press_data, period_start, period_end, shift_counts,job_counts)

    # ------------------------------------------------------------------
    # Step 1 — Read and deduplicate
    # ------------------------------------------------------------------

    def _read_and_deduplicate(self, path: Path) -> list[dict]:
        """
        Read all rows from the CSV, skip header, deduplicate.
        Dedup key: (machine_name, op_code, op_name, time_str)
        Returns a list of raw row dicts.
        """
        seen = set()
        rows = []

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader)  # skip header row

            for row in reader:
                # Skip rows too short to contain our columns
                if len(row) <= self.COL_TOTAL_TIME:
                    continue

                machine  = row[self.COL_MACHINE].strip()
                op_code  = str(row[self.COL_OP_CODE]).strip()
                op_name  = row[self.COL_OP_NAME].strip()
                time_str = row[self.COL_TIME].strip()

                # Only process machines we recognize
                if machine not in MACHINE_MAP:
                    continue

                dedup_key = (machine, op_code, op_name, time_str)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                rows.append({
                    "machine":     machine,
                    "op_code":     op_code,
                    "op_name":     op_name,
                    "time_str":    time_str,
                    "gross_str":   row[self.COL_GROSS].strip(),
                    "net_str":     row[self.COL_NET].strip(),
                    "total_str":   row[self.COL_TOTAL_TIME].strip(),
                })

        return rows

    # ------------------------------------------------------------------
    # Step 2 — Aggregate into per-press buckets
    # ------------------------------------------------------------------

    def _aggregate(self, rows: list[dict]) -> dict:
        """
        Walk each deduplicated row and accumulate into per-press buckets.

        Returns a dict keyed by press_id:
        {
            "3450": {
                "net_sheets": int,
                "gross_sheets": int,
                "actual_run_hrs": float,
                "total_logged_hrs": float,   # from col 31, read once
                "no_crew_hrs": float,
                "planned_maintenance_hrs": float,
                "downtime_by_lever": {"jams": float, "makeready": float, ...},
            },
            ...
        }
        """
        data = {}
        run_code      = PRODUCTIVE["run"]
        no_crew_code  = EXCLUDED["no_crew"]
        planned_code  = EXCLUDED["planned_maint"]

        for row in rows:
            press_id = MACHINE_MAP[row["machine"]]
            op_code  = row["op_code"]
            hours    = _parse_hms(row["time_str"])

            # Initialize press bucket on first encounter
            if press_id not in data:
                data[press_id] = {
                    "net_sheets":              0,
                    "gross_sheets":            0,
                    "actual_run_hrs":          0.0,
                    "total_logged_hrs":        0.0,
                    "no_crew_hrs":             0.0,
                    "planned_maintenance_hrs": 0.0,
                    "downtime_by_lever":       {k: 0.0 for k in LEVERS},
                    "downtime_by_code":        {},  # {code: {"hours": float, "name": str}}
                    "_total_set":              False,  # flag: col 31 read yet?
                }

            bucket = data[press_id]

            # Col 31 — total logged hrs. Read once per press (same value every row).
            if not bucket["_total_set"] and row["total_str"]:
                bucket["total_logged_hrs"] = _parse_hms(row["total_str"])
                bucket["_total_set"] = True

            # Route by op code
            if op_code == run_code:
                bucket["actual_run_hrs"] += hours
                # Sheets can't be negative — Auto-Count over-run accounting
                # occasionally logs negative waste. Floor at zero here.
                bucket["net_sheets"]     += max(_safe_int(row["net_str"]), 0)
                bucket["gross_sheets"]   += max(_safe_int(row["gross_str"]), 0)

            elif op_code == no_crew_code:
                bucket["no_crew_hrs"] += hours

            elif op_code == planned_code:
                bucket["planned_maintenance_hrs"] += hours

            elif op_code in LEVER_CODE_TO_CATEGORY:
                category = LEVER_CODE_TO_CATEGORY[op_code]
                bucket["downtime_by_lever"][category] += hours
                # Per-code detail for the deep-dive view
                code_entry = bucket["downtime_by_code"].setdefault(
                    op_code, {"hours": 0.0, "name": row["op_name"]}
                )
                code_entry["hours"] += hours

            # All other codes: acknowledged but not modeled (breaks, training, etc.)

        # Clean up the internal flag before returning
        for bucket in data.values():
            del bucket["_total_set"]

        return data

    # ------------------------------------------------------------------
    # Step 3 — Build Press objects
    # ------------------------------------------------------------------

    def _build_presses(self, press_data: dict, period_start, period_end,
                       shift_counts: dict = None, job_counts:dict=None) -> list[Press]:
        """
        Convert aggregated dicts into frozen Press dataclass instances.
        Skips any press with zero run hours (no productive data found).

        shift_counts: optional dict of press_id -> int from Machine Log parser.
        If not provided, total_shifts defaults to 0.
        """
        shift_counts = shift_counts or {}
        job_counts = job_counts or {}
        presses = []

        for press_id, bucket in press_data.items():
            if bucket["actual_run_hrs"] == 0:
                print(f"[WARNING] {press_id}: no run hours found — skipping")
                continue

            # Auto-Count can report gross < net due to over-run accounting.
            # Clamp gross to net minimum so the Press dataclass stays valid.
            gross = max(bucket["gross_sheets"], bucket["net_sheets"])

            press = Press(
                press_id               = press_id,
                period_start           = period_start,
                period_end             = period_end,
                net_sheets             = bucket["net_sheets"],
                gross_sheets           = gross,
                actual_run_hrs         = round(bucket["actual_run_hrs"], 2),
                total_logged_hrs       = round(bucket["total_logged_hrs"], 2),
                no_crew_hrs            = round(bucket["no_crew_hrs"], 2),
                planned_maintenance_hrs= round(bucket["planned_maintenance_hrs"], 2),
                total_shifts           = shift_counts.get(press_id, 0),
                job_count              = job_counts.get(press_id, 0), 
                downtime_by_lever      = {
                    k: round(v, 2)
                    for k, v in bucket["downtime_by_lever"].items()
                },
                downtime_by_code       = {
                    code: {"hours": round(d["hours"], 2), "name": d["name"]}
                    for code, d in bucket["downtime_by_code"].items()
                },
            )
            presses.append(press)

        return sorted(presses, key=lambda p: p.press_id)

    # ------------------------------------------------------------------
    # Step 4 — Parse shift counts from Machine Log (optional)
    # ------------------------------------------------------------------

    def parse_shifts(self, machine_log_path) -> tuple[dict, dict]:

        from datetime import timedelta

        machine_log_path = Path(machine_log_path)
        if not machine_log_path.exists():
            print(f"[WARNING] Production Log not found: {machine_log_path} — shifts and jobs will be 0")
            return {}, {}

        ML_MACHINE      = 7
        ML_TIME         = 25
        ML_SHIFT_MARKER = 53
        ML_SHIFT_DATE   = 26
        ML_ROW_TYPE     = 12
        ML_JOB          = 13

        DAY_START   = 7
        NIGHT_START = 19

        shift_sets   = {}
        job_sets     = {}
        current_machine = None

        with open(machine_log_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) <= ML_SHIFT_MARKER:
                    continue

                machine = row[ML_MACHINE].strip()
                if machine in MACHINE_MAP:
                    current_machine = MACHINE_MAP[machine]

                if current_machine is None:
                    continue

                # Job rows
                if row[ML_ROW_TYPE].strip() == "Job":
                    job_str = row[ML_JOB].strip()
                    job_num = job_str.split("-")[0].strip() if job_str else None
                    if job_num:
                        job_sets.setdefault(current_machine, set()).add(job_num)

                # Shift total rows
                if row[ML_SHIFT_MARKER].strip() != "Shift total":
                    continue

                press_id   = current_machine
                shift_date = row[ML_SHIFT_DATE].strip()
                time_str   = row[ML_TIME].strip()

                if not shift_date or not time_str:
                    continue

                try:
                    hour = int(time_str.split(":")[0])
                    parts = shift_date.split("/")
                    op_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
                except (ValueError, IndexError):
                    continue

                if DAY_START <= hour < NIGHT_START:
                    shift_window = ("day", op_date)
                elif hour >= NIGHT_START:
                    shift_window = ("night", op_date)
                else:
                    shift_window = ("night", op_date - timedelta(days=1))

                shift_sets.setdefault(press_id, set()).add(shift_window)

        shift_counts = {pid: len(windows) for pid, windows in shift_sets.items()}
        job_counts   = {pid: len(jobs) for pid, jobs in job_sets.items()}
        return shift_counts, job_counts


