# FloorPlan — Press Room Decision Engine (Portfolio Edition)

A bidirectional decision engine for a sheetfed press room floor manager,
built with Python and Streamlit. It is not a dashboard — it answers two
questions:

1. **Backward:** "I need 10% more sheets this month. Which levers do I pull?"
2. **Forward:** "I fixed the feeder on press 3670. What did I actually gain?"

Every downtime hour in the source data is categorized into controllable
levers (jams, makeready, approval waits, materials waits, shift handoff,
unplanned maintenance), converted to sheets via each press's measured
running speed, and ranked by recoverable output.

## ⚠️ About the data

This is a **portfolio fork** of a tool originally built against real
production exports. All identifying information has been removed:

- Press numbers, plant asset codes, and machine names are fictional
- Every metric in `data/snapshot.json` (sheets, hours, shifts, jobs) has
  been statistically perturbed — the data keeps the *shape* of real
  press-room behavior but is not any company's actual figures
- Documentation tables in `markdowns/` were rewritten the same way

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Access code on the launch screen: `demo`

## How it works

```
app.py                    Streamlit UI — four modes: Biggest Losses,
                          Path to Target, Build a Plan, Deep Dive
floorplan_calculator.py   Compatibility adapter: loads data, averages/totals
                          month ranges, exposes the calculation API to the UI
models/press.py           Frozen Press dataclass — one instance per press-month
parsers/                  CSV parsers for the shop-floor system's monthly
                          exports + snapshot generator/reader
calculations/             Pure functions: baseline speed/availability/ceiling,
                          per-lever impact, fleet rollup
config/op_codes.py        Single source of truth: operation code → lever mapping
data/snapshot.json        Six months of (synthetic) per-press production data
markdowns/                Design docs: calculation spec, architecture,
                          decision log
```

Core model, per press:

```
running_speed_net = net_sheets / actual_run_hrs        (measured, all-in)
available_hours   = logged_hrs - no_crew - planned_maintenance
lever impact      = hours_recovered × running_speed_net
```

## Tests

```bash
python -m pytest tests/test.py -v
```

Locks the averaged per-press and fleet baselines computed from the bundled
snapshot, so refactors to the parser/calculation layers can't silently
change the numbers.
