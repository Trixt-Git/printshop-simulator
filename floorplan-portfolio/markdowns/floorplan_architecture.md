> **⚠️ PARTIALLY OUTDATED — May 2026**
> This document predates the production rebuild. Parts of it no longer match
> the built system. The current sources of truth are:
> - `floorplan_calculations.md` — current calculation spec
> - `decisions.md` — every design decision and why (D1–D10)
> Treat this file as historical context, not current truth.

---

# FloorPlan — Production Architecture

How a Python developer would structure the clean rebuild. Pseudo-code, not implementation.

**Scope:** This doc covers two phases. **v1** is the production rebuild matching the calculations spec — parsers, models, calculations, UI. **v2** adds historical data and saved plans, deferred until v1 is proven in real use.

-----

## v1 — Production rebuild

## Guiding principles

- Separation of concerns: parsing, calculation, and UI never touch each other directly
- Pure functions for math: no hidden state, no side effects, easy to test
- Single source of truth: every variable defined once, imported everywhere it’s needed
- Fail loud: bad data raises clear errors instead of silently degrading
- Easy to swap data sources: CSV today, API tomorrow

-----

## File structure

```
floorplan/
├── __init__.py
├── parsers/
│   ├── __init__.py
│   ├── productivity_csv.py   # parses the Productivity by Machine CSV
│   └── base.py               # abstract base — defines what every parser returns
├── models/
│   ├── __init__.py
│   ├── press.py              # Press dataclass + validation
│   └── lever.py              # Lever dataclass + category-to-op-code mapping
├── calculations/
│   ├── __init__.py
│   ├── baseline.py           # running speeds, available hours
│   ├── ceiling.py            # ceiling sheets, opportunity sheets
│   ├── oee.py                # diagnostic OEE breakdown
│   ├── levers.py             # forward calculation (lever impact)
│   ├── planner.py            # backward calculation (path to target)
│   └── fleet.py              # fleet rollup
├── config/
│   ├── __init__.py
│   ├── op_codes.py           # operation code → lever category mapping
│   └── press_specs.py        # cruising speeds (manufacturer specs)
├── ui/
│   └── app.py                # Streamlit entry point (unchanged interface)
└── tests/
    └── test_*.py             # one test file per calculation module
```

-----

## Core data structures

### `models/press.py`

```python
@dataclass(frozen=True)
class Press:
    press_id: str                    # "3450"
    net_sheets: int
    gross_sheets: int
    actual_run_hrs: float
    total_logged_hrs: float
    no_crew_hrs: float
    planned_maintenance_hrs: float
    cruising_speed: int              # from press_specs.py
    downtime_by_lever: dict[str, float]  # {"jams": 56.4, "unplanned_maint": 224.4, ...}
```

A `Press` is immutable. Once built from the parser, no calculation modifies it. Calculations take a `Press` in, produce a result, return it.

### `models/lever.py`

```python
LEVERS = {
    "unplanned_maintenance": ["2011"],
    "breakdowns":            ["2000", "2001"],
    "jams":                  ["2070", "2085", "2086", "2087", "2097"],
    "shift_handoff":         ["2040"],
    "materials_wait":        ["2090", "2095"],
    "quality_wait":          ["2120", "2123"],
    "approval_wait":         ["2080", "2121", "2122", "2124", "2125"],
    "makeready":             ["1000", "1010"],
}
```

Lever-to-op-code mapping lives here and only here. If a code’s categorization changes, one place to edit.

-----

## Parser

### `parsers/base.py`

```python
class ProductivityParser(ABC):
    @abstractmethod
    def parse(self, source) -> list[Press]:
        """Take a data source, return a list of fully-populated Press objects."""
```

Why abstract: today the source is a CSV file. Tomorrow it’s the Auto-Count API. Anything that produces `list[Press]` works.

### `parsers/productivity_csv.py`

```python
class ProductivityCSVParser(ProductivityParser):
    def parse(self, csv_path) -> list[Press]:
        rows = self._read_unique(csv_path)
        return [self._build_press(p_id, rows) for p_id in MACHINE_MAP]

    def _read_unique(csv_path):
        # Read CSV, dedupe repeated rows by (machine, op_code, time)
        pass

    def _build_press(press_id, rows):
        # Filter rows for this press
        # Sum hours by op code
        # Sum sheets where op_code == "1020"
        # Build downtime_by_lever dict using LEVERS mapping
        # Return Press(...)
        pass
```

All CSV-specific knowledge (column indexes, machine name format, time parsing) lives in this one file. Calculations never know they came from a CSV.

-----

## Calculations

Each calculation module is pure functions. Takes a `Press` in, returns a result. No state, no side effects.

### `calculations/baseline.py`

```python
def running_speed_gross(press) -> float:
    return press.gross_sheets / press.actual_run_hrs

def running_speed_net(press) -> float:
    return press.net_sheets / press.actual_run_hrs

def available_hours(press) -> float:
    return press.total_logged_hrs - press.no_crew_hrs - press.planned_maintenance_hrs
```

### `calculations/ceiling.py`

```python
def ceiling_sheets(press) -> int:
    return round(available_hours(press) * running_speed_net(press))

def opportunity_sheets(press) -> int:
    return ceiling_sheets(press) - press.net_sheets
```

### `calculations/oee.py`

```python
def availability(press) -> float:
    return press.actual_run_hrs / available_hours(press)

def performance(press) -> float:
    return running_speed_gross(press) / press.cruising_speed

def quality(press) -> float:
    return press.net_sheets / press.gross_sheets

def oee(press) -> float:
    return availability(press) * performance(press) * quality(press)
```

### `calculations/levers.py`

```python
@dataclass(frozen=True)
class LeverResult:
    press_id: str
    category: str
    reduction_pct: float
    hours_recovered: float
    hours_used: float
    sheets_gained: int
    gap_closed_pct: float

def lever_impact(press, category, reduction_pct, hours_already_claimed=0) -> LeverResult:
    downtime_hrs = press.downtime_by_lever[category]
    hours_recovered = downtime_hrs * reduction_pct
    headroom = available_hours(press) - press.actual_run_hrs - hours_already_claimed
    hours_used = min(hours_recovered, headroom)
    sheets_gained = round(hours_used * running_speed_net(press))
    gap_closed = sheets_gained / opportunity_sheets(press)
    return LeverResult(...)
```

### `calculations/planner.py`

```python
def rank_levers(presses, reduction_pct=0.20) -> list[LeverResult]:
    """Return all fleet levers sorted by sheets_gained descending."""
    pass

def path_to_target(presses, target_sheets) -> list[LeverResult]:
    """Walk ranked levers until cumulative gain ≥ gap to target."""
    pass

def build_plan(presses, moves: list[tuple]) -> list[LeverResult]:
    """User-defined plan. Each move = (press_id, category, reduction_pct).
       Tracks hours_already_claimed per press across moves."""
    pass
```

### `calculations/fleet.py`

```python
def fleet_summary(presses) -> dict:
    """Aggregate per-press calculations into fleet-level metrics."""
    pass
```

-----

## Why this structure

**Pure calculation functions** mean every formula in the spec maps directly to a function. The Equations section of the spec doc is the table of contents for the `calculations/` folder.

**Press is immutable** so calculations are referentially transparent — calling `ceiling_sheets(press)` always returns the same value. No mutation bugs, no order-of-operation dependencies.

**Parser is swappable** because everything downstream only knows about `Press` objects. The UI doesn’t know if data came from a CSV, an API, or a mock for testing.

**Config separate from logic** — when manufacturer cruising speeds arrive, only `config/press_specs.py` changes. No calculation code edits.

**One-to-one mapping with the spec** — every section in `floorplan_calculations.md` has a matching module. Easy to verify completeness, easy to onboard a new developer.

-----

## Testing approach

Each calculation module gets a corresponding test file. Tests use fabricated `Press` objects with known values to verify the math.

```python
def test_ceiling_sheets():
    press = Press(
        press_id="TEST",
        net_sheets=1_000_000,
        gross_sheets=1_050_000,
        actual_run_hrs=100,
        total_logged_hrs=200,
        no_crew_hrs=20,
        planned_maintenance_hrs=10,
        cruising_speed=10_000,
        downtime_by_lever={},
    )
    # available = 200 - 20 - 10 = 170
    # running_speed_net = 1_000_000 / 100 = 10_000
    # ceiling = 170 * 10_000 = 1_700_000
    assert ceiling_sheets(press) == 1_700_000
```

This lets you verify spec changes don’t break the math. If the spec says “ceiling = available × running speed (net)” and the test passes, the calculation matches the spec.

-----

## UI principles (v1)

Three design decisions that shape how the floor manager experiences the tool. Each is small but materially changes what the tool feels like to use daily.

### Scenarios, not targets

Reduction percentage controls (the forward view sliders, the plan builder) are framed as “what if” scenarios, not commitments. Labels read “what if jams dropped by 20%” not “reduce jams by 20%.”

Why it matters: the floor manager uses the tool to make analytical cases upward. Target-framing creates risk that non-operators set goals based on tool output without context. Scenario-framing keeps the manager in the driver’s seat — the tool quantifies possibilities, he decides what’s realistic.

### “Why this matters” context on every result

Each lever result surfaces one sentence of context beyond the headline number. Examples:

- “+200K sheets — jams on 3220 are the third-highest downtime category fleet-wide”
- “+352K sheets — would lift 3450 from 27.9% to 33.2% utilization at current pace”

No new calculations — just surface what’s already computed alongside the result. Helps the manager explain results upward without having to look up context separately.

### Current vs prior snapshot comparison

The losses view (and key KPIs) show deltas against the prior month, not just absolute values. Example: “3340 jams: 82 hrs (▲15 vs prior month).”

This is the smallest possible version of trend analysis — one prior snapshot stored, one delta computed, no full historical system. It gives the floor manager the *what changed* signal that operational experts care most about, without scope-creeping into v2’s full historical layer.

Implementation note: requires storing the prior month’s snapshot. Not full historical persistence — just N=1. When a new snapshot ingests, the prior one rolls over.

### Running speed transparency

Every lever result displays the underlying running speed used in its calculation. Example: “Calculated at 7,807 sph (current running speed).”

Why it matters: the floor manager will challenge any number that doesn’t feel right. Showing the speed used in each calculation lets him verify the math himself — and trust it when his gut says the result is fishy. Without this, “the tool said +200K sheets” sounds like a black box. With it, he can see exactly where the number came from.

Non-negotiable for implementation. Easy to drop under deadline pressure, but this is the difference between a tool managers trust and one they ignore.

-----

# v2 — Deferred features

The sections below extend v1. **Build only when v1 is proven in real use and these specific value props are justified by user behavior.** Listed here so the design thinking is captured, not lost.

-----

## Historical data layer

Three years of monthly Productivity exports turn the tool from “what does this month look like” into “is what we’re doing actually working.” Same calculations, run against any historical snapshot.

```
floorplan/
├── data/
│   ├── __init__.py
│   ├── store.py              # SQLite wrapper for snapshots and preferences
│   ├── snapshot.py           # capture a parsed Press list as a dated record
│   ├── archive.py            # store raw CSVs alongside processed snapshots
│   └── trends.py             # query helpers for period-over-period analysis
```

**What gets stored:**

- Raw CSV files preserved on disk, hashed and indexed by month
- Processed snapshots (list of Press objects) stored in SQLite, keyed by calendar month
- Both kept, so reprocessing with updated op-code logic is possible later

**Snapshot granularity:**

Calendar-month aligned. CSV exports covering arbitrary date ranges get bucketed into their primary month. This keeps trend lines comparable without complicated time-window math.

**The killer use case:**

> “We worked on jams reduction for two months. Did jams hours actually drop, and did production rise as predicted?”

The trend module compares predicted lever gains against actual measured changes once new snapshots arrive. Validates the model, surfaces drift, and tells the manager whether his interventions worked.

**Trend analysis is its own subsystem.** Period comparison, moving averages, anomaly detection, and confounder handling each need real design work. Build the storage layer first, design trend analysis once specific questions emerge from real use.

-----

## Preferences and saved plans

Same SQLite database, separate tables. Stores what the manager wants to come back to.

```
data/
├── user_state.py             # last-used filters, default values
└── plans.py                  # named, multi-lever plans with results
```

**User state — simple key-value:**

- Last-used press, category, reduction %
- Default view (forward / backward / losses / plan)
- UI preferences

**Saved plans — proper data model:**

A plan is a name, a created date, and a list of moves. Each move is a press + category + reduction %. Plans get queried, edited, and shared. Worth a dedicated table:

```
plans
├── plan_id (PK)
├── name
├── created_at
├── snapshot_month        # which baseline this plan was built against
└── notes

plan_moves
├── move_id (PK)
├── plan_id (FK)
├── press_id
├── category
├── reduction_pct
└── sequence
```

**One-plant scope assumptions:**

- Single shared “manager” user — no auth yet
- SQLite on shared drive or app server — no Postgres
- Manual CSV ingestion — admin drops file, script ingests it as new snapshot
- No real-time updates — refresh happens on snapshot ingestion

-----

## Migration path

The proof-of-concept stays as `floorplan_app.py` for the purchaser demo. The production build sits in `floorplan/` as a parallel codebase. When ready, point the Streamlit app at the new modules and retire the old code.

No incremental migration. Clean rewrite.