# FloorPlan — Core Engineering Concepts

*Built during the FloorPlan production rebuild. Each concept explained in context of real code written.*

---

## How to use this file

Each concept has:
- **What it is** — plain english definition
- **Real world analogy** — something from print ops or business
- **Why it matters** — what goes wrong without it
- **Where it lives in FloorPlan** — the actual file and line

Quiz yourself by covering everything below the concept name and trying to explain it out loud before reading.

---

## Concepts

---

### Dataclass

**What it is**
A shortcut for writing classes in Python. You declare the fields and their types, and Python auto-generates the boring boilerplate (`__init__`, `__repr__`, etc.) for you.

**Real world analogy**
A pre-printed form. Instead of writing out "Name: ___, Date: ___, Press ID: ___" from scratch every time, the form already has the fields laid out. You just fill them in.

**Why it matters**
Without it you'd write every field twice — once in `__init__` parameters and once as `self.field = field`. Dataclasses eliminate that repetition and make the structure of your data immediately readable.

**Where it lives in FloorPlan**
`models/press.py` — `@dataclass(frozen=True) class Press`

---

### Frozen Dataclass

**What it is**
A dataclass with `frozen=True` — once built, no field can be changed. Any attempt to modify a field raises a `FrozenInstanceError` immediately.

**Real world analogy**
A completed job ticket written in pen, not pencil. The source record is permanent. If something was wrong, you issue a corrected ticket — you don't erase the original.

**Why it matters**
Without it, a calculation deep in the system could accidentally overwrite a field on the Press object. The error would be silent — wrong numbers, no crash, no warning. Freezing means the data is trustworthy from the moment it's built to the moment the app closes.

**Where it lives in FloorPlan**
`models/press.py` — `@dataclass(frozen=True)`

---

### `__post_init__`

**What it is**
A special method on a dataclass that runs automatically after `__init__` finishes. Used to add validation logic without rewriting the constructor.

**Real world analogy**
A QC check at the end of a press run. The press runs (data gets loaded), then before the job ships (object gets used) someone checks that the sheet count isn't negative and the gross isn't less than net.

**Why it matters**
Catches impossible data at the moment of construction — not 5 files later when a calculation produces a nonsense result. The error message points directly at the data problem.

**Where it lives in FloorPlan**
`models/press.py` — `def __post_init__(self)`

---

### Single Source of Truth

**What it is**
One place in the codebase where a piece of information lives. Everything else that needs it reads from that one place rather than maintaining its own copy.

**Real world analogy**
A chart of accounts in accounting. Every department references the same account numbers. Nobody keeps their own private version of what account 5100 means.

**Why it matters**
If the same information exists in multiple places, they drift out of sync. You update one and forget the other. Now you have a silent bug — the system runs without crashing but produces wrong answers.

**Where it lives in FloorPlan**
`config/op_codes.py` — `LEVERS` dict is the single source of truth for all op code categorization. `LEVER_CODE_TO_CATEGORY` and the per-code detail in `downtime_by_code` both derive from it.

---

### DRY — Don't Repeat Yourself

**What it is**
An engineering principle: every piece of knowledge should exist in exactly one place in a system. If you find yourself writing the same thing in two places, that's a signal to extract it into a shared location.

**Real world analogy**
If every department at the print shop kept their own copy of the press schedule and updated it independently, they'd always be out of sync. One shared schedule that everyone reads from is DRY.

**Why it matters**
Repetition means every change requires finding and updating every copy. Miss one and you have inconsistency. DRY means one change, one place, system-wide effect.

**Where it lives in FloorPlan**
`config/op_codes.py` — op codes defined once, imported everywhere they're needed.

---

### Dictionary Lookup vs. Linear Search

**What it is**
Two ways to find something. Linear search checks items one by one until it finds a match — speed depends on how many items you have. Dictionary lookup computes a hash and jumps directly to the answer — speed is constant regardless of size.

**Real world analogy**
Linear search is flipping through a stack of job tickets one by one looking for job #4821. Dictionary lookup is having an index tab — you go directly to the right section.

**Why it matters**
For thousands of CSV rows each needing a category lookup, linear search compounds. Dictionary lookup does it in the same time whether you have 10 op codes or 10,000.

**Where it lives in FloorPlan**
`config/op_codes.py` — `LEVER_CODE_TO_CATEGORY` is built specifically for fast lookup in the parser.

---

### Index (derived data structure)

**What it is**
A second copy of data reorganized for fast access. Built automatically from the primary source so they never go out of sync. Redundant by design — the point is speed, not storage efficiency.

**Real world analogy**
A database index on a column you query frequently. Same concept your SQL class covered — the database maintains a separate structure so it can find rows without scanning the whole table.

**Why it matters**
`LEVERS` is organized for human readability (category → list of codes). `LEVER_CODE_TO_CATEGORY` is the index — organized for machine lookup (code → category). Same data, different shape, different purpose.

**Where it lives in FloorPlan**
`config/op_codes.py` — `LEVER_CODE_TO_CATEGORY` generated from `LEVERS` via dict comprehension.

---

### Dict Comprehension

**What it is**
A one-line way to build a dictionary by looping over another data structure. Same idea as list comprehension but produces a dict instead of a list.

**Real world analogy**
A mail merge. You have a list of names and addresses (source data) and you generate one envelope per person (output dict) automatically — not by hand.

**Why it matters**
Generates `LEVER_CODE_TO_CATEGORY` automatically from `LEVERS`. If you maintained it manually, adding one op code to `LEVERS` and forgetting to add it to the lookup dict would create a silent bug.

**Where it lives in FloorPlan**
`config/op_codes.py`:
```python
LEVER_CODE_TO_CATEGORY = {
    code: category
    for category, codes in LEVERS.items()
    for code in codes
}
```

---

### Abstract Base Class (ABC)

**What it is**
A class that defines a contract — a set of methods that any subclass must implement. Cannot be used directly. Exists only to be inherited from.

**Real world analogy**
A job description. It defines what anyone in the role must be able to do. The job description itself doesn't do any of the work — the person hired into the role does.

**Why it matters**
Guarantees that every parser — CSV, API, database, whatever comes next — exposes the same interface. The calculations layer doesn't need to know which parser it's talking to. It just knows the contract is honored.

**Where it lives in FloorPlan**
`parsers/base.py` — `class ProductivityParser(ABC)`

---

### `@abstractmethod`

**What it is**
A decorator that marks a method as required. Any class that inherits from the ABC must implement this method or Python raises a `TypeError` at the moment you try to create an instance.

**Real world analogy**
A mandatory certification. You can't start operating the press without it. The system checks before you're allowed to start, not after something goes wrong mid-run.

**Why it matters**
Catches missing implementations immediately — at object creation, not later when the missing method is called and something silently produces wrong output or crashes.

**Where it lives in FloorPlan**
`parsers/base.py` — `@abstractmethod def parse(self, source, machine_log=None) -> list[Press]`

---

### Programming to an Interface

**What it is**
Writing code that depends on a contract (what something can do) rather than a specific implementation (how it does it). The calling code doesn't know or care what's behind the curtain.

**Real world analogy**
A USB port. Your laptop doesn't know if you've plugged in a flash drive, a keyboard, or a camera. It just knows the USB contract — power and data protocol. Any device that honors the contract works.

**Why it matters**
The calculations layer works identically whether you pass it a CSV parser or an API parser. Swap the data source without touching a single line of calculation code.

**Where it lives in FloorPlan**
`parsers/base.py` defines the interface. The parsers implement it; the rest of the package programs to it.

---

### Pipeline Pattern (ETL)

**What it is**
A one-way transformation where data flows through distinct stages, each with one job. Raw input → cleaned data → structured output. Also called Extract, Transform, Load in data engineering.

**Real world analogy**
A press job moving through the plant. Prepress (extract) → pressroom (transform) → bindery (load). Each stage has one job. Output of one stage is input to the next. Nothing flows backwards.

**Why it matters**
Makes debugging precise. If output numbers are wrong you know exactly which stage to inspect. Also makes each stage independently testable and replaceable.

**Where it lives in FloorPlan**
`parsers/productivity_csv.py` — `_read_and_deduplicate` → `_aggregate` → `_build_presses`

---

### Snapshot vs. Time Series

**What it is**
A snapshot captures one moment in time. A time series is a collection of snapshots with timestamps, enabling trend analysis, comparisons, and history.

**Real world analogy**
One monthly P&L report is a snapshot. Three years of monthly P&L reports filed in order is a time series — now you can see trends, seasonality, year-over-year comparisons.

**Why it matters**
Adding `period_start` and `period_end` to `Press` transformed FloorPlan from a single-month tool into a system that can answer questions like "has makeready been improving over the last 36 months?"

**Where it lives in FloorPlan**
`models/press.py` — `period_start: date` and `period_end: date` fields.

---

### Accumulator Pattern

**What it is**
Starting a variable at zero (or empty) and adding to it as you loop through data. By the end of the loop, it holds the total.

**Real world analogy**
Running a tally sheet during a press run. Every 1,000 sheets you make a mark. At the end of the shift the total marks give you the run count — you didn't hold every individual count in your head.

**Why it matters**
The parser doesn't store individual CSV rows — it accumulates totals. By the time the loop ends, `actual_run_hrs` holds the full month's run hours for that press without ever needing to store all the individual events.

**Where it lives in FloorPlan**
`parsers/productivity_csv.py` — `_aggregate()` method, `bucket["actual_run_hrs"] += hours`

---

### Defensive Programming

**What it is**
Writing code that anticipates bad input and handles it gracefully rather than crashing or producing wrong output silently.

**Real world analogy**
A press operator who checks paper moisture before starting a run even when nobody told them to. You don't wait for the job to jam — you check first.

**Why it matters**
CSV exports are messy. Rows can be too short, time strings can be malformed, sheet counts can be empty. Without defensive checks, one bad row crashes the entire parse. With them, bad rows are skipped or defaulted to zero and the good data still processes.

**Where it lives in FloorPlan**
`parsers/productivity_csv.py` — `_parse_hms()` returns 0.0 on bad input, `_safe_int()` returns 0 on bad input, row length check before column access.

---

### Lambda

**What it is**
A throwaway function with no name, written inline for a single use. Identical to a named function but defined in one line and discarded after use.

**Real world analogy**
Giving someone a sorting rule for a stack of job tickets. "Sort by due date" is the rule — you say it once, they use it, it doesn't need a name or a permanent home.

**Why it matters**
When you need to pass a simple function as an argument (to `sorted()`, Pandas `apply()`, `groupby()`, etc.) writing a full named function is unnecessary overhead. Lambda lets you write the rule inline where it's used.

**The long way vs lambda**
```python
# Named function — necessary if reused or complex
def get_sheets(result):
    return result.sheets_gained

sorted(results, key=get_sheets, reverse=True)

# Lambda — same thing, inline, throwaway
sorted(results, key=lambda r: r.sheets_gained, reverse=True)
```

**Where you'll see this**
Constantly in Pandas — `df.apply(lambda row: row["net"] / row["gross"])`, `df.groupby("press_id").apply(lambda g: g.tail(3))`. Same concept every time.

**The core idea**
Use a lambda when the function is one line and never needed again. If it's complex or reused — write a real named function.

**Where it lives in FloorPlan**
`calculations/levers.py` — `sorted(results, key=lambda r: r.sheets_gained, reverse=True)`

---

### Pure Function

**What it is**
A function that takes inputs and returns an output with no side effects. Same input always produces same output. Nothing outside the function changes when it runs.

**Real world analogy**
A conversion chart. 1 inch is always 25.4mm. The chart doesn't remember what you looked up last time, doesn't change based on who's asking, doesn't affect anything else in the room.

**Why it matters**
Pure functions are trivially testable — no database, no file system, no app state needed. Build a Press with known numbers, call the function, check the result. Pass or fail instantly. Also makes debugging precise — if the output is wrong, the problem is in the inputs, not hidden state somewhere else.

**Where it lives in FloorPlan**
`calculations/baseline.py` and `calculations/levers.py` — every function takes a Press and returns a number or LeverResult.

---

### Generator Expression

**What it is**
Like a list comprehension but without square brackets. Calculates values one at a time and passes them directly to whatever is consuming them, without building a full list in memory first.

**Real world analogy**
Reading job tickets one at a time and calling out the sheet count vs. writing every sheet count on a separate piece of paper first and then adding them up. Same result, less intermediate work.

**Why it matters**
More memory efficient than a list comprehension when you only need the result once (like passing directly into `sum()`). For small datasets the difference is negligible — it's good habit for when data gets large.

**Where it lives in FloorPlan**
`calculations/levers.py` — `sum(r.sheets_gained for r in results)`

---

### Slice Notation

**What it is**
A way to grab a portion of a list using `[start:end]` syntax. Negative indices count from the end. `[-3:]` means "last 3 items to the end."

**Real world analogy**
Pulling the last 3 monthly reports from a filing cabinet. You don't read the whole cabinet — you go to the end and pull back 3.

**Why it matters**
Makes time-series operations readable and concise. Critical for rolling window calculations — grab the last N months without knowing the total length of the list.

**Where it lives in FloorPlan**
Rolling 90-day average — `last_3_months = [p for p in all_presses if p.press_id == "3450"][-3:]`

---

### Function Composition

**What it is**
Building bigger functions out of smaller ones. A function calls other functions to do its work instead of recalculating everything itself.

**Real world analogy**
A shift supervisor doesn't personally count every sheet. They ask the press operator for the run count and the scheduler for available time, then combine those answers. Each person has one job; the supervisor composes their outputs.

**Why it matters**
`ceiling_sheets` doesn't know how to calculate available hours or running speed — it calls `available_hours()` and `running_speed_net()`. If the formula for available hours ever changes, you change it in one place and everything that composes it updates automatically. No duplicated math.

**Where it lives in FloorPlan**
`calculations/baseline.py` — `ceiling_sheets()` calls `available_hours()` and `running_speed_net()` rather than recomputing them.

---

### Guard Clause

**What it is**
A check at the top of a function that handles a bad or edge-case input immediately — usually by returning early — before the main logic runs.

**Real world analogy**
Checking the press has paper loaded before you hit run. You don't get halfway through the job and then discover the problem — you check the blocking condition first and stop right there if it fails.

**Why it matters**
Prevents crashes from impossible inputs. `oee_availability` divides by available hours — if that's zero, dividing crashes the app. The guard clause checks `if avail <= 0: return 0.0` first, so the division is only ever reached when it's safe.

**Where it lives in FloorPlan**
`calculations/baseline.py` — `oee_availability()` and `oee_quality()` both guard against a zero denominator before dividing.

---

### Separation of Concerns

**What it is**
Keeping distinct responsibilities in distinct places. What something *is* (data) stays separate from what something *does* (logic), and defining a thing stays separate from running it.

**Real world analogy**
A cookbook is not the act of cooking. The recipe (definition) sits on the shelf doing nothing until a cook (the caller) opens it and follows it. You don't write the recipe fresh every time you cook — and you don't bake instructions into the act of eating.

**Why it matters**
The `floorplan/` package is layered exactly this way: `models/` holds data, `parsers/` transforms input, `calculations/` holds pure logic, the UI displays. Each layer can be tested, debugged, or replaced without disturbing the others. The React migration only has to replace the UI layer — the package underneath is untouched.

**Where it lives in FloorPlan**
The whole package structure — `models/`, `parsers/`, `config/`, `calculations/` are separate folders by design, each with one concern.

---

### Adapter Pattern

**What it is**
A thin translation layer that lets two incompatible pieces of code work together. It exposes the interface one side expects, but fulfills it using the other side.

**Real world analogy**
A travel power adapter. Your laptop charger expects a US socket; the wall in another country provides a different one. The adapter doesn't generate power — it just translates the shape of the connection so the two fit.

**Why it matters**
The Streamlit UI was written against the old proof-of-concept calculator. Rather than rewrite the finished UI, `floorplan_calculator.py` was built as an adapter — it exposes the exact function names and return shapes the UI imports, but every result is produced by the audited `floorplan/` package. The UI never knew its backend was swapped out.

**Where it lives in FloorPlan**
`floorplan_calculator.py` — exposes `fleet_summary`, `rank_opportunities`, etc. (old names), powered by the new package. See decision D12.

---

*Last updated: FloorPlan production rebuild, May 2026*
*Add new concepts here as they're introduced in each session.*
