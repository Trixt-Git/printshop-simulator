# FloorPlan — Open Questions & Decisions Log

*Track unresolved questions before they become bugs or rework.*

---

## Open Questions

### Q1 — Gross vs Net as primary sheet metric
**Raised by:** Purchaser conversation
**Context:** Floor managers can verify gross sheets directly on the press counter. Net requires waste adjustment which isn't visible in real time.
**Options:**
- Calculate and display in net (current approach — conservative, accurate)
- Calculate and display in gross (easier floor verification, but inflated lever impact numbers)
- Calculate in net, display both (best of both — verify on floor, business case stays conservative)
**Decision needed from:** Purchaser + plant manager
**Status:** OPEN

---

### Q2 — Cruising speed (manufacturer rated SPH) per press
**Status:** CLOSED — see D5

---

## Decisions Made

### D1 — Monthly CSV exports, filename convention
**Decision:** Export one CSV per month. The filename must contain a `YYYY_MM`
pattern (e.g. `pressroom_2026_01.csv`) — the parser extracts the period from it
via regex `(\d{4})_(\d{2})`. The prefix is free; only the `YYYY_MM` token matters.
**Rationale:** One file per month keeps data clean, enables time-series analysis,
and supports the planned 90-day rolling average. Period-from-filename means no
manual date entry and files self-sort chronologically.
**Date:** May 2026

### D2 — Two-report parser: Productivity by Machine + Machine Log
**Decision:** The parser uses TWO Auto-Count reports. Productivity by Machine is
the primary source (op codes, sheet counts, times, total logged hours). The
Machine Log is a secondary source used only for shift counting.
**History:** An earlier plan was to rebuild around the Production Log report as
a single source. That was reversed — the Production Log export only contains
shift-total summary rows with no per-operation op-code detail, so it cannot
produce downtime by lever. Productivity by Machine was kept as primary; the
abandoned Production Log parser was archived (see D10).
**Known caveat:** Productivity by Machine `total_logged_hrs` (col 31) can
include idle wall-clock time. Flagged as an open item in floorplan_calculations.md.
**Date:** May 2026

### D3 — Op code categorization (locked)
**Decision:** Final LEVERS mapping in config/op_codes.py
**Additions from real CSV:** 2021→makeready, 2096→materials_wait, 2088→maintenance, 1050→maintenance, 2079→makeready, 2041→shift_handoff, 2078→jams, 2081→quality_wait, 2089→shift_handoff
**Date:** May 2026

### D4 — Shift classification logic
**Decision:** Shift counts come from the Machine Log's "Shift total" summary
rows (not from scanning individual operations). Each shift-total row is
deduplicated, then classified by its start time:
- Day shift:   07:00–18:59 → counted on the shift's date
- Night shift: 19:00–23:59 → counted on the shift's date
- Night shift: 00:00–06:59 → counted on the previous calendar day
`total_shifts` = count of unique (shift_type, shift_date) windows per press.
**Assumption:** at most one day and one night shift per calendar date — true
for the 7am/7pm two-shift schedule.
**Date:** May 2026

### D5 — OEE Performance metric dropped, using internal metric
**Decision:** Do not use manufacturer rated cruising speed for OEE Performance ratio. Fleet is 15+ years old — manufacturer spec is not a meaningful benchmark.
**Replacement:** Use `running_speed_net` as the primary performance metric. This reflects actual real-world output and is directly comparable period over period.
**Impact:** `cruising_speed` and `oee_performance()` were subsequently removed — see D6.
**Date:** May 2026

### D6 — OEE simplified to two standalone diagnostics
**Decision:** Removed `oee_performance` and `oee_overall`. Kept `oee_availability` and `oee_quality` as separate diagnostic numbers — no combined "OEE" score.
**Rationale:** Performance requires a manufacturer rated speed to compare against. With no meaningful rated speed (D5), there is no theoretical target left, so Performance cannot be computed honestly. Availability and Quality compare against real measured quantities and remain valid. A faked two-factor "OEE" was rejected as misleading.
**Also removed:** `running_speed_gross` (only caller was Performance).
**Date:** May 2026

### D7 — Headroom logic removed entirely
**Decision:** Removed all headroom apparatus from `levers.py` and `baseline.py` — `headroom_hours`, the `hours_already_claimed` parameter, recovery capping, `headroom_limited`/`headroom_remaining`/`hours_requested` fields.
**Rationale:** Lever hours are a percentage of downtime that already occurred. Recovered hours are physically self-limiting — you can never recover more than was lost. The headroom cap can never trigger, so it added complexity with zero function.
**Date:** May 2026

### D8 — Negative sheet counts floored at zero
**Decision:** In the parser's `_aggregate`, sheet counts are floored at zero with `max(value, 0)`. `_safe_int` itself stays general-purpose (parses negatives honestly); the business rule lives where sheets are counted.
**Rationale:** Auto-Count over-run accounting occasionally logs negative waste. Negative sheets are physically impossible. Option B from audit — surgical floor at the point of use, not in the helper.
**Date:** May 2026

### D9 — Planner fails loud on unknown levers
**Decision:** `build_plan` validates every lever name against the known lever set and raises ValueError on any unknown name. Also guards against empty press list.
**Rationale:** Consistency with `lever_impact` which already raised. The planner is backend-only — no user free-text input — so loud failure on a typo'd lever is correct. "Always yell."
**Date:** May 2026

### D10 — Superseded code archived, not deleted
**Decision:** `production_log_csv.py` and `press_specs.py` moved to `floorplan/_archive/` with a README explaining why each is dead. Not imported by live code.
**Rationale:** Keeps history and reasoning available without risk of accidental import.
**Date:** May 2026

### D11 — Per-op-code downtime detail (Deep Dive)
**Decision:** The `Press` dataclass carries `downtime_by_code` — a dict of
`{op_code: {"hours": float, "name": str}}` — alongside `downtime_by_lever`.
The parser accumulates per-code hours and captures the operation name from
CSV col 21. The adapter exposes `code_breakdown()` and `code_labels_by_category()`.
**Rationale:** A re-audit found the Deep Dive view was running on two hardcoded
dictionaries (`DOWNTIME_CODE_MAP`, `CODE_HOUR_SPLITS`) baked into the UI with
stale pre-D3 data. It rendered without error but silently omitted nine op codes
and showed numbers that did not reconcile with the rest of the app. Capturing
per-code detail as real parsed data killed both hardcoded dicts permanently and
made the Deep Dive self-maintaining — new op codes and renamed operations flow
through automatically.
**Verification:** per-code totals reconcile with per-lever totals to <0.1%, and
Deep Dive category totals reconcile with the Losses view.
**Date:** May 2026

### D12 — Compatibility adapter between UI and package
**Decision:** `floorplan_calculator.py` is a compatibility adapter, not the
calculation engine. It exposes the exact function names and return shapes the
existing Streamlit UI imports (`fleet_summary`, `rank_opportunities`,
`what_would_it_take`, `lever_impact`, `DEFAULT_PRESS_CONFIG`,
`DEFAULT_DOWNTIME_CONFIG`), but every result is produced by the audited
`floorplan/` package running on real CSV data.
**Rationale:** The UI design was already finished and was not to be rebuilt.
The adapter lets the audited backend power the existing UI unchanged, and
becomes the clean API boundary for the planned React migration.
**Note:** the UI's `speed` lever is synthetic — handled in the adapter as a
"what if the press ran faster" scenario, deliberately kept out of the clean
`levers.py` since running speed is measured reality, not a lever.
**Date:** May 2026
