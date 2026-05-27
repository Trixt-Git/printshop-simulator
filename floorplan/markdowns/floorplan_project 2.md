> **⚠️ PARTIALLY OUTDATED — May 2026**
> This document predates the production rebuild. Parts of it no longer match
> the built system. The current sources of truth are:
> - `floorplan_calculations.md` — current calculation spec
> - `decisions.md` — every design decision and why (D1–D10)
> Treat this file as historical context, not current truth.

---

# FloorPlan — Project Documentation
*RRD Press Room Decision Engine*
*Last updated: May 2026*

---

## What This Is

FloorPlan is a bidirectional decision engine for the RRD press room floor manager. It is not a dashboard. It does not run live. It answers two questions:

1. **Backward:** "My boss needs 10% more sheets this month. What do I pull?"
2. **Forward:** "I fixed the feeder on 2500. What did I actually gain?"

The tool is calibrated to real production data from Q1–April 2026 and produces output in sheets — the floor manager's currency.

---

## The Problem It Solves

The press room produces data. Auto-Count captures every operation, every downtime event, every sheet run. But none of that data was connected to a decision. Reports told the floor manager what happened. Nothing told him what to do next.

FloorPlan closes that gap. It takes real operational data, translates it into a mathematical model of the press room, and lets the floor manager move levers to see the impact before committing to a course of action.

---

## Project Origin

Built by Wil Uhlir (RRD print operations) as a proof of concept to demonstrate analytical capability to leadership and support a move toward an internal data analyst role. Started as a synthetic simulation (trading card print shop), pivoted to real data after a 2.5-hour meeting with the purchaser resulted in full data access.

**Masters program context:** ISM data analytics program starting Summer 2026. This project is the head start on ISM 645 Predictive Analytics (Fall 2026).

---

## Data Sources

### Auto-Count (ePS Platform)
The production data system. Every press event is logged at the operation level.

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
| P4-30201 | 2060 | KBA105 — Sheetfed |
| P4-30202 | 2190 | KBA106 PCUV — Sheetfed |
| P4-30203 | 2160 | 840 Komori — Sheetfed |
| P4-30204 | 2500 | 640 Komori — Sheetfed |
| P4-30206 | 2330 | 640 Komori — Sheetfed |
| P4-30207 | 2150 | 640 Komori — Sheetfed |

### Radius (pending)
Cost and estimating system. Job-level quoting and actual cost data. Access approved, fulfillment pending. When available, will enable dollar-based output alongside sheets.

### Plant Manager
Floor scheduling and production system. Job routing, sequence data, downstream department tracking (die cut, foil stamp, etc.). Access confirmed. Job sequence analysis pinned for future phase.

---

## Press Fleet — April 2026 Calibration

| Press | Night Shift | Days Run (Apr) | Avg Run Hrs/Month | Effective SPH | Cruising SPH | OEE % |
|-------|------------|---------------|------------------|--------------|-------------|-------|
| 2190 | ✓ | 24 | 218.3 | 7,839 | 8,070 | 39.4% |
| 2160 | ✓ | 29 | 140.0 | 5,777 | 7,540 | 15.5% |
| 2150 | ✓ | 26 | 160.5 | 6,829 | 8,530 | 21.6% |
| 2500 | — | 35 | 143.1 | 6,980 | 7,765 | 33.3% |
| 2330 | — | 22 | 50.4  | 5,780 | 7,085 | 21.6% |
| 2060 | — | 28 | 36.4  | 8,117 | 9,490 | 6.6%  |

**Notes:**
- Effective SPH = net sheets / actual run hours. Lower than cruising SPH due to job mix, startup cycles, foil runs.
- Cruising SPH = median speed during 1020 Run events on white stock.
- OEE = Availability × Performance × Quality. Industry average 60%, world class 85%.
- Calibration averaged across Q1 2026 (Jan–Mar monthly avg) + April 2026.
- 2060 confirmed Sheetfed — not Perfecting despite original fleet definition. Fix applied.

---

## Downtime Baseline — Q1–April 2026 Average (hrs/month)

| Press | Approval Wait | Quality Wait | Materials Wait | Shift Handoff | Maintenance | Jams |
|-------|-------------|-------------|---------------|--------------|------------|------|
| 2190 | 5.2 | 9.2 | 1.6 | 17.0 | 224.4 | 56.4 |
| 2160 | 9.3 | 6.1 | 9.5 | 7.5  | 115.4 | 88.4 |
| 2150 | 1.8 | 9.7 | 27.8 | 3.8 | 156.4 | 104.4 |
| 2500 | 3.4 | 3.8 | 8.3  | 4.2 | 125.0 | 62.8 |
| 2330 | 0.4 | 0.8 | 5.2  | 2.7 | 46.1  | 32.2 |
| 2060 | 0.9 | 21.0 | 7.9 | 10.1 | 127.6 | 60.3 |

**No Crew / Downtime/Idle (excluded from levers — scheduling decision):**
- 2330: ~482 hrs/month — press sits idle more than half the month
- 2060: ~358 hrs/month — crew availability is the primary constraint

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
| Press | Calc | Real | Diff |
|-------|------|------|------|
| 2190 | 1,711,254 | 1,537,245 | +11.3% |
| 2160 | 808,780 | 859,957 | -6.0% |
| 2150 | 1,096,054 | 1,268,807 | -13.6% |
| 2500 | 998,838 | 1,044,403 | -4.4% |
| 2330 | 291,312 | 389,954 | -25.3% |
| 2060 | 295,459 | 215,474 | +37.1% |
| **Fleet** | **5,201,697** | **5,315,840** | **-2.1%** |

Fleet-level accuracy is within 2%. Per-press variance is higher on low-volume presses (2330, 2060) due to scheduling volatility. Accuracy improves with more months of data.

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

**Fleet OEE: 28.8%** — well below industry average of 60%. 12 million sheets of untapped capacity between reality (5.3M/month) and ceiling (17.4M/month).

**2190 maintenance dominates** — 224 hrs/month of maintenance vs 218 hrs of actual run time. The best maintained press in the fleet spends more time being maintained than running.

**2160 partial run problem** — 5.9 makeready events per shift vs 2-3 for every other press. Spending as much time on setup as printing. 145 hrs of Make Ready 2 (1010) vs 150 hrs of actual run in April.

**2330 barely running** — 22 shifts in April, 50 hrs of run time. Mostly sitting idle. Question of whether jobs should route to 2500 instead.

**2060 quality approval** — 21 hrs/month of quality approval wait on a press that only runs 36 hrs. 58% of run time blocked waiting for QC sign-off.

**2500 jams** — 390 jam events in April, highest in fleet. Feeder issue confirmed. Rainbow board stock causes the most significant speed penalty (34% drop vs white stock).

**Foil/rainbow stock speed penalty:**
- 2160: -7.2% (confirmed, n=36)
- 2150: -10.7% (low sample)
- 2500: -34.4% (low sample, high confidence the penalty is real)

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

1. Pull **Productivity By Machine** report from Auto-Count for the most recent month
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
- **Greg Cholmondeley (Keypoint Intelligence)** — print MIS expert. Tool surfaces what Auto-Count captures but nobody acts on. Data freshness matters — automate the pull when API access comes through.

---

## Open Items

**Pinned for data/access:**
- [ ] Radius access — dollar cost per press hour, enables revenue-weighted lever ranking
- [ ] Plant Manager job sequence data — which job transitions cause makeready spikes
- [ ] Auto-Count API access — automate monthly recalibration instead of manual CSV exports
- [ ] Night shift assignments for 2500, 2330, 2060 — confirm from scheduling data
- [ ] Billing rate structure — confirm with estimating how passes affect billing (flagged in simulation code)

**Pinned for future phases:**
- [ ] Job sequence analysis — does running foil back-to-back reduce makeready vs alternating with white?
- [ ] Operator-level performance analysis — does output vary by operator on specific presses? (HR conversation needed first)
- [ ] Die cut / foil stamping downstream — currently out of scope, separate model
- [ ] Revenue weighting — foil sheets worth more than white, weight lever rankings by margin not just sheets
- [ ] Scheduling optimization — partial run reduction (2160 running 6 jobs/shift vs 2-3 for others)

**Known calibration gaps:**
- Age factors in simulation are estimated, not calibrated — pin until job-level data available
- 2500 foil SPH is low confidence (n=2 in April data)
- 2330 per-press accuracy is lower due to scheduling volatility
- PrintFlow system data disregarded — new system, not yet calibrated

---

## Next Steps

1. **May data** — pull Productivity By Machine for May, recalibrate with 5-month average
2. **Radius access** — follow up with purchaser on fulfillment timeline
3. **Floor manager meeting** — put the tool in front of him. Ask: what does he look at first in the morning, what's in his control, what language does he use for these problems
4. **API access** — request Auto-Count API credentials from IT
5. **Controller conversation** — billing rates, cost per press hour, overrun policy

---

## Portfolio Note

This project is intentionally industry-agnostic in its architecture. The decision engine pattern — calibrate from real operational data, surface controllable levers, translate between target and action — applies to any manufacturing operation with time-based throughput constraints.

For portfolio/resume purposes: "Built a bidirectional operational decision engine on top of 4 months of real press room data, calibrating a 6-press fleet model to within 2% of actual net production at the fleet level."
