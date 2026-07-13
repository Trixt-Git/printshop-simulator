> **⚠️ PARTIALLY OUTDATED — May 2026**
> This document predates the production rebuild. Parts of it no longer match
> the built system. The current sources of truth are:
> - `floorplan_calculations.md` — current calculation spec
> - `decisions.md` — every design decision and why (D1–D10)
> Treat this file as historical context, not current truth.

---

# Print Ops Decision Engine — Calculator Logic
*Captured: May 1, 2026*

---

## North Star Metric
**Sheets Produced** — the floor manager's daily goal. Everything else is either a driver or a cost.

---

## Core Formula

```
Sheets Produced = (Available Hours - Total Downtime) × SPH
```

Simple at the top level. The work is in accurately accounting for every hour lost.

---

## Available Hours (Monthly Ceiling)

- 12 hour shifts, 1 hour breaks = **11 productive hours per shift**
- Plant runs 7 days a week

| Press | Shifts | Available Hrs/Month |
|-------|--------|-------------------|
| 3450 | Day + Night | 242 hrs |
| 3220 | Day + Night | 242 hrs |
| 3340 | Day + Night | 242 hrs |
| 3670 | Day only | 121 hrs |
| 3560 | Day only | 121 hrs |
| 3110 | Day only | 121 hrs |

*Night shift assignments for 3670, 3560, 3110 to be confirmed against Plant Manager data.*

---

## Levers

### Speed (SPH)
Fixed characteristic of each press — not a lever the floor manager pulls daily, but sets the ceiling for what's possible.
- SPH varies by press
- Foil runs slower than white
- 121-up vs 100-up affects output per sheet

### Downtime (Hours Lost)
Every category below is an input the floor manager can adjust in the calculator. The model converts hours lost directly to sheets lost.

| Downtime Type | Owner | Fix Strategy |
|--------------|-------|-------------|
| Waiting on manager approval | Process | Approval workflow |
| Waiting on quality approval | Process | QC response time |
| Waiting on materials | Supply chain | Material staging |
| Shift handoff | Scheduling | Handoff protocol |
| Scheduled maintenance | Maintenance | PM scheduling |
| Jams (mechanical) | Operator/mechanical | Maintenance, operator training |

### Job Mix
- Which press gets which job type
- Foil vs white ratio
- 121-up vs 100-up ratio
- Customer mix / run size distribution

### Makeready
- Time per makeready (minutes)
- Number of makereadies per job — partial runs create 3+ makereadies on a single job, each one eating available time and generating waste

---

## What's Excluded (This Phase)
- Age/condition factor — treated as a given, not a lever. "What would it take with the resources we have now."
- Die cutting / foil stamping downstream — press room only for now
- Scheduling optimization — future project

---

## Accuracy Target
- Acceptable: within 50,000 sheets
- Goal: within 10,000 sheets
- Directional reliability beats precision

---

## Open Items
- Confirm night shift assignments for 3670, 3560, 3110 from Plant Manager data
- Get actual SPH by press from real data (currently estimated)
- Confirm how partial runs are logged — separate press entries on same job number?
- Get full downtime code list from Plant Manager to map to categories above
- Confirm makeready time logging — separate code or bundled into run time?
