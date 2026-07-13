> **⚠️ PARTIALLY OUTDATED — May 2026**
> This document predates the production rebuild. Parts of it no longer match
> the built system. The current sources of truth are:
> - `floorplan_calculations.md` — current calculation spec
> - `decisions.md` — every design decision and why (D1–D10)
> Treat this file as historical context, not current truth.

> **📢 PORTFOLIO FORK NOTE**
> This is a public portfolio fork. Press numbers, machine identifiers, and all
> production metrics in this repository (including the tables below and
> `data/snapshot.json`) have been renamed and statistically perturbed. The
> numbers preserve the shape and relationships of real press-room data but are
> not any company's actual figures.

---

# FloorPlan — Project Documentation
*Press Room Decision Engine*
*Last updated: May 2026*

---

## What This Is

FloorPlan is a bidirectional decision engine for a press room floor manager. It is not a dashboard. It does not run live. It answers two questions:

1. **Backward:** "My boss needs 10% more sheets this month. What do I pull?"
2. **Forward:** "I fixed the feeder on 3670. What did I actually gain?"

The tool is calibrated to monthly production exports from Q1–April 2026 and produces output in sheets — the floor manager's currency.

---

## The Problem It Solves

The press room produces data. The shop-floor data system captures every operation, every downtime event, every sheet run. But none of that data was connected to a decision. Reports told the floor manager what happened. Nothing told him what to do next.

FloorPlan closes that gap. It takes operational data, translates it into a mathematical model of the press room, and lets the floor manager move levers to see the impact before committing to a course of action.

---

## Project Origin

Built as a proof of concept that shop-floor production data can drive floor-level decisions. Started as a synthetic simulation (trading card print shop), then rebuilt around real monthly production exports once data access was secured. This public fork replaces that data with anonymized, perturbed equivalents.

---

## Data Sources

### Auto-Count (production data system)
Every press event is logged at the operation level.

**Reports used:**
- **Productivity By Machine** — monthly summary report. Gives run hours, gross/net sheets, and downtime by operation code per press. Used for calibration.
- **Production Log** — detailed weekly CSV exports. Gives job-level operation sequences with timestamps, speeds, and sheet counts. Used for analysis.

**Key operation codes:**
| Code | Meaning | Calculator category |
|------|---------|-------------------|
| 1020 | Run | Run time |
| 1000 / 1010 | Make Ready / Make Ready 2 | Makeready |
| 2000 / 2001 / 2070 / 2085–2087 / 2097 | Breakdowns, jams, feeder problems | Jams |
| 2010 / 2011 / 2075 / 2082 / 2083 / 2088 | Maintenance planned/unplanned, wash, blanket/plate change | Maintenance |
| 2080 / 2081 / 2121 / 2122 | Approval waits | Manager Approval |
| 2120 / 2123 / 2076 | Quality waits, set-up adjustment | Quality Approval |
| 2090 / 2095 / 2096 | Material waits | Materials Wait |
| 2040 / 2041 | Shift change, waiting for crew | Shift Handoff |
| 2060 | Downtime/No Crew | **Excluded** — scheduling decision, not floor lever |

**Press machine IDs:**
| Machine ID | Press | Type |
|-----------|-------|------|
| L2-40201 | 3110 | Apex 105 — Sheetfed |
| L2-40202 | 3450 | Apex 106 PCUV — Sheetfed |
| L2-40203 | 3340 | 840 Vector — Sheetfed |
| L2-40204 | 3670 | 640 Vector — Sheetfed |
| L2-40206 | 3560 | 640 Vector — Sheetfed |
| L2-40207 | 3220 | 640 Vector — Sheetfed |

### Cost/estimating system (pending)
Job-level quoting and actual cost data. When available, will enable dollar-based output alongside sheets.

### Scheduling system
Floor scheduling and production system. Job routing, sequence data, downstream department tracking (die cut, foil stamp, etc.). Job sequence analysis pinned for future phase.

---

## Press Fleet — April 2026 Calibration

| Press | Night Shift | Days Run (Apr) | Avg Run Hrs/Month | Effective SPH | Cruising SPH | OEE % |
|-------|------------|---------------|------------------|--------------|-------------|-------|
| 3450 | ✓ | 25 | 231.6 | 7,610 | 7,890 | 37.8% |
| 3340 | ✓ | 27 | 149.2 | 5,930 | 7,720 | 16.4% |
| 3220 | ✓ | 28 | 151.7 | 7,050 | 8,240 | 22.9% |
| 3670 | — | 32 | 135.4 | 7,210 | 8,010 | 31.5% |
| 3560 | — | 20 | 54.8  | 5,540 | 6,890 | 20.3% |
| 3110 | — | 26 | 39.9  | 7,860 | 9,180 | 7.2%  |

**Notes:**
- Effective SPH = net sheets / actual run hours. Lower than cruising SPH due to job mix, startup cycles, foil runs.
- Cruising SPH = median speed during 1020 Run events on white stock.
- OEE = Availability × Performance × Quality. Industry average 60%, world class 85%.
- Calibration averaged across Q1 2026 (Jan–Mar monthly avg) + April 2026.
- 3110 confirmed Sheetfed — not Perfecting despite original fleet definition. Fix applied.

---

## Downtime Baseline — Q1–April 2026 Average (hrs/month)

| Press | Approval Wait | Quality Wait | Materials Wait | Shift Handoff | Maintenance | Jams |
|-------|-------------|-------------|---------------|--------------|------------|------|
| 3450 | 4.7 | 10.1 | 1.8 | 15.4 | 241.2 | 52.1 |
| 3340 | 8.5 | 6.8 | 8.7 | 8.2  | 123.8 | 81.6 |
| 3220 | 2.1 | 8.9 | 25.3 | 4.2 | 144.9 | 112.7 |
| 3670 | 3.1 | 4.3 | 7.6  | 4.6 | 117.2 | 68.4 |
| 3560 | 0.5 | 0.9 | 4.7  | 2.4 | 50.3  | 29.8 |
| 3110 | 1.0 | 18.9 | 8.6 | 9.2 | 138.1 | 55.7 |

**No Crew / Downtime/Idle (excluded from levers — scheduling decision):**
- 3560: ~440 hrs/month — press sits idle more than half the month
- 3110: ~385 hrs/month — crew availability is the primary constraint

---

## Core Math

```
Sheets = Available Hours × OEE × Cruising SPH

OEE = Availability × Performance × Quality

Availability = Actual Run Hours / Available Hours
Performance  = Effective SPH / Cruising SPH  (calibrated from real data)
Quality      = Net Sheets / Gross Sheets

Available Hours = Days Scheduled × Shifts per Day × 11 hrs per shift
```

**Key design decisions:**
- **11 hrs per shift** — 12hr shift minus 1hr breaks
- **Reality baseline** = actual run hours × effective SPH. Reproduces April net sheets within 0.0% at fleet level.
- **Ceiling** = available hours × cruising SPH × performance × quality. What's theoretically possible.
- **Lever impact** = hours recovered × effective SPH, capped at available headroom (available hours − actual run hours).
- **No Crew excluded** — not a floor lever. Reduces the ceiling conceptually but is not surfaced as something he can change.
- **Planned maintenance** — fixed input per month, reduces available hours before lever calculations.

**April validation:**
| Press | Calc | Actual | Diff |
|-------|------|--------|------|
| 3450 | 1,648,930 | 1,481,270 | +11.3% |
| 3340 | 852,410 | 906,220 | -5.9% |
| 3220 | 1,184,720 | 1,371,540 | -13.6% |
| 3670 | 941,050 | 983,970 | -4.4% |
| 3560 | 315,880 | 422,860 | -25.3% |
| 3110 | 272,110 | 198,420 | +37.1% |
| **Fleet** | **5,215,100** | **5,364,280** | **-2.8%** |

Fleet-level accuracy is within 3%. Per-press variance is higher on low-volume presses (3560, 3110) due to scheduling volatility. Accuracy improves with more months of data.

---

## The Levers

Six controllable downtime categories, split by type:

**Process levers** (people/workflow)
- Approval Wait — manager sign-off delays
- Quality Wait — QC approval delays
- Materials Wait — stock not staged
- Shift Handoff — transition time between shifts

**Mechanical levers** (equipment)
- Jams & Breakdowns — mechanical stops, feeder issues, electrical
- Unplanned Maintenance — breakdowns requiring repair, wash, blanket/plate changes

**Not a lever:**
- Scheduled/planned maintenance — input by floor manager as a fixed reduction
- No Crew / idle time — scheduling decision above floor manager level
- SPH — press characteristic, not directly controllable day-to-day

---

## Key Findings from Data Analysis

**Fleet OEE: 27.9%** — well below industry average of 60%. Roughly 13 million sheets of untapped capacity between reality (5.4M/month) and ceiling (17.8M/month).

**3450 maintenance dominates** — 241 hrs/month of maintenance vs 232 hrs of actual run time. The best maintained press in the fleet spends more time being maintained than running.

**3340 partial run problem** — 5.6 makeready events per shift vs 2-3 for every other press. Spending as much time on setup as printing. 133 hrs of Make Ready 2 (1010) vs 149 hrs of actual run in April.

**3560 barely running** — 20 shifts in April, 55 hrs of run time. Mostly sitting idle. Question of whether jobs should route to 3670 instead.

**3110 quality approval** — 19 hrs/month of quality approval wait on a press that only runs 40 hrs. Nearly half of run time blocked waiting for QC sign-off.

**3670 jams** — ~360 jam events in April, highest in fleet. Feeder issue confirmed. Rainbow board stock causes the most significant speed penalty (~32% drop vs white stock).

**Foil/rainbow stock speed penalty:**
- 3340: -6.8% (confirmed, n=36)
- 3220: -11.6% (low sample)
- 3670: -31.9% (low sample, high confidence the penalty is real)

---

## File Structure

```
floorplan_app.py        — Streamlit decision engine UI (run this)
floorplan_calculator.py — Core math layer (OEE-based, no UI)
floorplan_parser.py     — Auto-Count CSV parser (production log format)
```

**Running the tool:**
```bash
streamlit run floorplan_app.py
```

**Parser usage:**
```python
from floorplan_parser import parse_all
df = parse_all("/path/to/csv/folder")
```

**Calculator usage:**
```python
from floorplan_calculator import fleet_summary, what_would_it_take, DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG

fleet = fleet_summary(DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)
result = what_would_it_take(6_000_000, DEFAULT_PRESS_CONFIG, DEFAULT_DOWNTIME_CONFIG)
```

---

## Recalibration Process

The calculator is calibrated to Q1–April 2026. To update with new data:

1. Pull the **Productivity By Machine** report for the most recent month
2. Run the parser to extract run hours, net sheets, and downtime by category
3. Average with existing calibration data (weight by months)
4. Update `DEFAULT_PRESS_CONFIG` and `DEFAULT_DOWNTIME_CONFIG` in `floorplan_calculator.py`

Key values to update:
- `actual_run_hrs` — from 1020 Run events
- `effective_sph` — net sheets / run hours
- `quality` — net / gross sheets
- `days_scheduled` — from observed shift data
- All downtime category hours

---

## Expert Panel

Design validated against five expert perspectives:

**Data Visualization**
- **Edward Tufte** — high data-ink ratio, no decoration. Bullet graphs, waterfall chart, numbers with context.
- **Stephen Few** — bullet graphs for reality vs ceiling, target line on every chart, top 3 levers not a ranked list of 35.
- **Nick Desbarats** — decision-facilitating display, not a monitoring dashboard. The gap and the plan dominate. Two modes share state.

**Manufacturing Analytics**
- **Vorne/Nakajima (OEE.com)** — TAED principles. Keep it simple enough that he opens it. Absolute hours not percentages.
- **Greg Cholmondeley (Keypoint Intelligence)** — print MIS expert. Tool surfaces what the data system captures but nobody acts on. Data freshness matters — automate the pull when API access comes through.

---

## Open Items

**Pinned for data/access:**
- [ ] Cost system access — dollar cost per press hour, enables revenue-weighted lever ranking
- [ ] Scheduling job sequence data — which job transitions cause makeready spikes
- [ ] Data system API access — automate monthly recalibration instead of manual CSV exports
- [ ] Night shift assignments for 3670, 3560, 3110 — confirm from scheduling data
- [ ] Billing rate structure — confirm with estimating how passes affect billing (flagged in simulation code)

**Pinned for future phases:**
- [ ] Job sequence analysis — does running foil back-to-back reduce makeready vs alternating with white?
- [ ] Operator-level performance analysis — does output vary by operator on specific presses? (HR conversation needed first)
- [ ] Die cut / foil stamping downstream — currently out of scope, separate model
- [ ] Revenue weighting — foil sheets worth more than white, weight lever rankings by margin not just sheets
- [ ] Scheduling optimization — partial run reduction (3340 running 6 jobs/shift vs 2-3 for others)

**Known calibration gaps:**
- Age factors in simulation are estimated, not calibrated — pin until job-level data available
- 3670 foil SPH is low confidence (n=2 in April data)
- 3560 per-press accuracy is lower due to scheduling volatility
- New scheduling system data disregarded — not yet calibrated

---

## Portfolio Note

This project is intentionally industry-agnostic in its architecture. The decision engine pattern — calibrate from real operational data, surface controllable levers, translate between target and action — applies to any manufacturing operation with time-based throughput constraints.

For portfolio/resume purposes: "Built a bidirectional operational decision engine on top of 4 months of press room data, calibrating a 6-press fleet model to within ~3% of actual net production at the fleet level."
