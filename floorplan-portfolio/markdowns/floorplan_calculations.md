# FloorPlan — Model Calculations

Complete spec: calculations, equations, and data sources.
**This document reflects the production rebuild as of May 2026.**
For the reasoning behind changes, see `decisions.md`.

---

## Per-Press Baseline

The current state of each press, monthly. One `Press` object per press per month.

The `Press` dataclass fields:

- **press_id** — e.g. "3450"
- **period_start / period_end** — the month this data covers
- **net_sheets** — good sheets the press made
- **gross_sheets** — total sheets produced including waste
- **actual_run_hrs** — hours the press was actively running (op code `1020`)
- **total_logged_hrs** — Auto-Count's per-press total logged time (see warning below)
- **no_crew_hrs** — hours with no crew scheduled (op code `2060`)
- **planned_maintenance_hrs** — scheduled PM hours (op code `2010`)
- **total_shifts** — number of shifts the press actually worked in the period
- **downtime_by_lever** — hours per lever category, e.g. `{"jams": 44.1, ...}`
- **downtime_by_code** — per-op-code detail: `{"2070": {"hours": 12.4, "name": "Jam"}, ...}`

Derived (not stored on Press, calculated by `baseline.py`):

- **available_hours** = total_logged_hrs − no_crew_hrs − planned_maintenance_hrs
- **running_speed_net** = net_sheets ÷ actual_run_hrs → used in ALL lever calculations

Note (decision D5): there is no cruising speed and no gross running speed in the
model. The fleet is 15+ years old — manufacturer rated speed is not a meaningful
benchmark. `running_speed_net` is a measured fact from real data and is the only
speed the model uses.

---

## ⚠️ Important: total_logged_hrs reliability

`total_logged_hrs` is read directly from CSV col 31 — it is Auto-Count's own
per-press total logged time. It is NOT derived by summing operation hours.

This number can include wall-clock monitoring time even when a press was idle
and unmanned. In sample data, press 3560 showed a very high `total_logged_hrs`
despite barely running. Treat `available_hours` (which is derived from it) with
this caveat in mind.

This is a known limitation carried from the data source. If it proves
materially misleading once monthly files are loaded, the fix is to derive
`total_logged_hrs` by summing logged operation hours instead. Flagged as an
open item.

---

## Per-Press Downtime

Hours lost per month, broken out two ways:
- **by lever** — aggregated into the 7 controllable categories below
- **by op code** — the raw per-code detail behind each lever (powers Deep Dive)

**Levers (controllable):**

- Maintenance (unplanned maintenance, mechanical + electrical breakdowns, ink roller maintenance, auto-restart)
- Jams (including web breaks)
- Shift handoff (including waiting for crew, one-person crew)
- Materials wait (including raw materials non-conformance)
- Quality wait (including waiting for color match)
- Approval wait (manager / sales / customer approval)
- Makeready (all setup, changeover, plate/blanket changes, wash-up, cleanup, ink conversion, waste removal)

*Note: Makeready has a practical floor — reductions are reasonable up to a point, not toward zero.*

**Productive operations (not downtime):**

- Run time (`1020`)
- Over running (`1030`) — currently captured by neither sheets nor downtime; see Open Items

**Excluded from model (not controllable):**

- No Crew (`2060`) — subtracted from available hours
- Planned maintenance (`2010`) — subtracted from available hours
- Breaks / lunch (`2030`) — acknowledged, not modeled
- Training / meetings (`2050`, `2118`) — acknowledged, not modeled

---

## Per-Press Ceiling

The achievable max output at current efficiency — not theoretical max.

- **Ceiling sheets** = available hours × running speed (net)
- Available hours already excludes No Crew and Planned Maintenance, so ceiling
  reflects what the press could produce if every available hour ran at the
  current realistic running rate.

---

## Per-Press Gap

- **Opportunity sheets** = ceiling sheets − net sheets
- The total recoverable production through lever improvements.

---

## Diagnostic Metrics

Used to explain *why* a press is at its current output level. Not used in lever
calculations. Reported as two separate numbers — there is no combined "OEE" score
(decision D6).

- **Availability** = actual run hours ÷ available hours
- **Quality** = net sheets ÷ gross sheets

Performance (actual speed vs. rated speed) was removed — it requires a
manufacturer rated speed that does not meaningfully exist for this fleet.

---

## Lever Impact (Forward Calculation)

What happens if we reduce one downtime category by X%.

- **Hours recovered** = downtime hours[category] × reduction %
- **Sheets gained** = hours recovered × running speed (net)
- **Gap closed %** = sheets gained ÷ opportunity sheets

Running speed (net sheets ÷ run hours) is used because recovered hours will run
at the same realistic rate as all other running hours on that press. The UI
displays the speed used in each calculation for transparency (explicit
stakeholder request).

Note (decision D7): there is no headroom cap. Lever hours are a percentage of
downtime that already occurred, so recovered hours are physically self-limiting —
the model can never recover more from "jams" than were actually logged as jams,
and total recovered hours can never exceed available time. An earlier design
included a headroom guardrail; it was removed because the cap can never trigger.

---

## Code-Level Detail (Deep Dive)

Each lever's total can be broken down to the individual op codes behind it,
using the `downtime_by_code` field on each Press.

- **Per-code hours** = real logged hours for that op code, from the parser
- **Per-code sheets** = per-code hours × running speed (net)
- **Per-code label** = the operation name as Auto-Count reports it (CSV col 21)

Per-code totals reconcile exactly with per-lever totals (verified to <0.1%).
The Deep Dive view uses this — no hardcoded code mappings or proportions.

---

## Path to Target (Backward Calculation)

Given a production target, identify the levers that close the gap.

- **Target sheets** = set by user, defaults to current net sheets × 1.10 (10% stretch)
- **Gap to target** = target sheets − net sheets
- **Ranked levers** = sort all fleet levers by sheets gained at default reduction %, descending
- **Cumulative selection** = walk down the list until cumulative sheets gained ≥ gap to target

---

## Fleet Rollup

Same metrics, summed across all presses.

- **Fleet net sheets** = Σ(net sheets per press)
- **Fleet ceiling** = Σ(ceiling sheets per press)
- **Fleet opportunity** = Σ(opportunity sheets per press)
- **Fleet availability** = Σ(run hours) ÷ Σ(available hours)
- **Fleet quality** = Σ(net sheets) ÷ Σ(gross sheets)

Fleet ratios are WEIGHTED — raw hours and sheets are summed first, then divided.
They are NOT the average of per-press percentages; a tiny press must not distort
the fleet number.

Per-press metrics drive action — a fleet availability of 30% could mean one
press at 60% pulling up five at 25%, or all presses at 30%. The dashboard
surfaces both.

---

## Equations

### Baseline

- `actual_run_hrs` — hours logged under operation code `1020` Run
- `running_speed_net = net_sheets / actual_run_hrs`
- `available_hrs    = total_logged_hrs − no_crew_hrs − planned_maintenance_hrs`
  - `total_logged_hrs` is read from CSV col 31 (Auto-Count's own total)

**Note on availability:** `available_hours` subtracts no-crew time. The
availability metric therefore measures only manned, runnable time. It is NOT
a staffing metric and the model never implies a headcount solution — every
recoverable sheet comes from a process lever (makeready, jams, maintenance,
approval waits), not from adding people.

### Ceiling and Gap

- `ceiling_sheets     = available_hrs × running_speed_net`
- `opportunity_sheets = ceiling_sheets − net_sheets`

### Diagnostics

- `availability = actual_run_hrs / available_hrs`
- `quality      = net_sheets / gross_sheets`

### Lever Impact (Forward)

- `hours_recovered = downtime_hrs[category] × reduction_pct`
- `sheets_gained   = hours_recovered × running_speed_net`
- `gap_closed_pct  = sheets_gained / opportunity_sheets`

Sheet counts (`ceiling_sheets`, `sheets_gained`) are truncated to whole
integers — you cannot produce a fraction of a sheet. Truncation is
deliberately conservative: it never rounds a count up.

### Code-Level Detail

- `code_hours  = downtime_by_code[code]["hours"] × reduction_pct`
- `code_sheets = code_hours × running_speed_net`

### Path to Target (Backward)

- `target_sheets   = net_sheets × (1 + growth_pct)`   ← or user-set absolute number
- `gap_to_target   = target_sheets − net_sheets`
- `ranked_levers   = sort(all_fleet_levers, by=sheets_gained, desc)`
- `selected_levers = walk ranked_levers, cumulative until sum(sheets_gained) ≥ gap_to_target`

### Fleet Rollup

- `fleet_net_sheets   = Σ(net_sheets per press)`
- `fleet_ceiling      = Σ(ceiling_sheets per press)`
- `fleet_opportunity  = Σ(opportunity_sheets per press)`
- `fleet_availability = Σ(actual_run_hrs) / Σ(available_hrs)`
- `fleet_quality      = Σ(net_sheets) / Σ(gross_sheets)`

---

## Source Mapping

### Data sources

The model uses two CSV reports (decision D2). The Productivity by Machine
report is required. The Machine Log is optional at the parser level — without
it the app still runs, but `total_shifts` is 0 and the mins-per-shift display
is unavailable. For correct output, supply both.

**Productivity by Machine** — event-level op code data. Key columns (0-based):

- Col 18 — Machine name (e.g., `L2-40202 - L2-3450 Apex106-PCUV-Sheetfed`)
- Col 20 — Operation code (e.g., `1020`, `2011`)
- Col 21 — Operation name (human-readable label, used for code detail)
- Col 23 — Time (HH:MM:SS) for that event row
- Col 25 — Gross sheets for that event row
- Col 27 — Net sheets for that event row
- Col 31 — Per-press total logged time

**Machine Log** — shift-level data, used only for shift counting. Key columns:

- Col 7  — Machine name
- Col 25 — Operation start time (HH:MM)
- Col 26 — Shift start date
- Col 53 — "Shift total" marker on shift summary rows

Files must be named with a `YYYY_MM` pattern (e.g. `pressroom_2026_01.csv`) so
the parser can derive the period. One file per month (decision D1).

### Per-press inputs

| Variable                  | Source                                          |
|---------------------------|--------------------------------------------------|
| `net_sheets`              | Sum of col 27 where op code = `1020`, floored ≥0 |
| `gross_sheets`            | Sum of col 25 where op code = `1020`, floored ≥0 |
| `actual_run_hrs`          | Sum of col 23 where op code = `1020`             |
| `total_logged_hrs`        | Read from col 31 (Auto-Count per-press total)    |
| `no_crew_hrs`             | Sum of col 23 where op code = `2060`             |
| `planned_maintenance_hrs` | Sum of col 23 where op code = `2010`             |
| `downtime_by_lever`       | Col 23 hours summed per lever category           |
| `downtime_by_code`        | Col 23 hours + col 21 name, per individual code  |
| `total_shifts`            | Count of unique shift windows (Machine Log)      |
| `running_speed_net`       | Calculated: `net_sheets / actual_run_hrs`        |

### Shift counting

Shifts are counted from the Machine Log's **"Shift total" summary rows**
(col 53), deduplicated, then classified by start time (decision D4):

- Day shift:   07:00–18:59 → shift date = the shift's date
- Night shift: 19:00–23:59 → shift date = the shift's date
- Night shift: 00:00–06:59 → shift date = the shift's date − 1 day

`total_shifts` is the count of unique (shift_type, shift_date) windows per press.

This assumes at most one day shift and one night shift per calendar date —
true for the 7am/7pm two-shift schedule. If two shift-total rows ever
classified into the same window, they would count as one.

### Per-press downtime by category

Each lever maps to one or more operation codes (decision D3 — validated against
real CSV data). Hours summed per press per code.

| Lever          | Op codes                                                              |
|----------------|-----------------------------------------------------------------------|
| Maintenance    | `2011`, `2000`, `2001`, `2088`, `1050`                                |
| Jams           | `2070`, `2085`, `2086`, `2087`, `2097`, `2078`                        |
| Shift handoff  | `2040`, `2041`, `2089`                                                |
| Materials wait | `2090`, `2095`, `2096`                                                |
| Quality wait   | `2120`, `2123`, `2081`                                                |
| Approval wait  | `2080`, `2121`, `2122`, `2124`, `2125`                                |
| Makeready      | `1000`, `1010`, `1060`, `2075`, `2076`, `2082`, `2083`, `2084`, `2021`, `2079` |

### Excluded codes

Tracked for completeness, not used in lever calculations:

- `2010` Planned maintenance — subtracted from available hours
- `2060` No Crew — subtracted from available hours
- `2030` Break/Lunch, `2050`/`2118` Training/Meetings — acknowledged, not modeled
- `1020` Run — productive
- `1030` Over Running — productive; currently not added to sheet counts (see Open Items)

---

## Open Items

- **Gross vs net as primary metric** — purchaser suggested gross is easier for
  floor managers to verify. Open question Q1 in decisions.md. Currently all
  calculations use net.
- **total_logged_hrs reliability** — read from col 31, which can include idle
  monitoring time. If misleading on monthly data, switch to deriving it from
  summed operation hours.
- **Over-run (`1030`)** — productive but currently captured by neither sheet
  counts nor downtime. Decide whether over-run sheets count toward net.
- **Makeready floor** — reductions should target a realistic minimum per press,
  not zero. Floor value still needs confirmation.
- **Rolling window** — 90-day rolling average planned once 3 years of monthly
  files are loaded. Data structure (period_start/period_end on Press) already
  supports it.
- **Press-specific codes** — how to handle op codes that appear on only one
  press (genuine reality vs. data quality issue).
