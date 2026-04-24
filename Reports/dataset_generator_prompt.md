# Prompt: Synthetic Manufacturing Dataset Toolkit

Use this prompt with any capable AI (ChatGPT, Gemini, etc.) to generate a similar
dataset toolkit for a different industry or operation. Replace the bracketed sections
with your own details.

---

## THE PROMPT

I work in [INDUSTRY] and want to build a synthetic operations dataset for data analysis
practice and portfolio projects. Please build me a complete toolkit with three
deliverables:

---

### 1. Dataset Generator (Python script)

Generate a realistic synthetic dataset with [NUMBER] rows where each row represents
one [UNIT OF WORK — e.g. job, order, batch, shift, transaction].

**Operation details:**
- [DESCRIBE YOUR OPERATION — e.g. "We run 5 machines: 3 older units (Machine-1,
  Machine-2, Machine-3) and 2 newer high-speed units (Machine-4, Machine-5)"]
- [DESCRIBE YOUR WORKFORCE STRUCTURE — e.g. "We have 4 shifts: Day A, Night A,
  Day B, Night B. Any machine can be used by any shift."]
- [DESCRIBE YOUR PRODUCT/MATERIAL TYPES — e.g. "All jobs use either standard stock
  or premium stock. Premium takes longer and has higher defect rates."]
- [DESCRIBE YOUR KEY PROCESS VARIABLES — e.g. "Key metrics are setup time, run time,
  waste %, defect rate, and on-time delivery."]
- [DESCRIBE YOUR COST STRUCTURE — e.g. "Costs include materials, machine time at
  different rates per machine type, labor, and rework."]

**Script requirements:**
- Put ALL scenario variables in a clearly labeled CONFIG block at the top of the
  script so I can change them without touching the generation logic
- Config should include: number of rows, date range, machine/shift names and weights,
  product mix, base performance parameters per machine, quality thresholds, cost rates,
  and markup/revenue range
- Older or lower-performing machines should have an age_factor > 1.0 that realistically
  degrades their waste, speed, and quality metrics
- Night or off-peak shifts should carry a small but realistic performance penalty
- Include realistic noise (normal/exponential distributions) so the data doesn't look
  synthetic
- Output a CSV and optionally a formatted Excel file with a summary dashboard sheet
- Print a summary to the console on every run showing key KPIs so scenarios can be
  compared quickly

**Columns to include:**
- Job/order identifiers and dates
- Operational assignment (machine, shift, product type, process config)
- Throughput metrics (quantity ordered, quantity produced, units run, waste)
- Time metrics (setup time, run time, total time, speed)
- Quality metrics (at least 3-4 relevant quality measurements + pass/fail flag)
- Rework/rerun flag and cost impact
- Full cost breakdown (materials, machine time, consumables, finishing, total)
- Revenue, gross profit, gross margin %
- Unit economics (cost per unit, revenue per unit)
- On-time delivery flag

---

### 2. Analysis Script (Python script)

Produce a separate analysis script that:
- Loads the CSV from the same directory
- Prints a KPI summary to the console (total revenue, margin, pass rate, rerun rate,
  total rerun cost, best/worst machine)
- Generates 6 charts saved as PNG files covering:
  1. Cost driver breakdown by product/material type
  2. Machine performance comparison (waste, quality, setup time)
  3. Shift performance comparison (waste, quality, rerun rate)
  4. Product type financial profile (margin, cost per unit, rerun rate)
  5. Waste % heatmap — machine × shift grid
  6. Rerun cost impact by machine and by shift
- Use a clean, professional color scheme (dark blue and red as primary colors,
  no default matplotlib styles)
- Remove top and right spines, use subtle background, label all bar values

---

### 3. README (Markdown file)

Write a README.md that covers:
- File list with descriptions
- Quick start (install dependencies, run commands)
- Dataset column reference
- Scenario modeling guide with 4-5 copy-paste CONFIG examples
- Chart output reference table
- 5 portfolio project ideas relevant to the industry

---

### Formatting rules for all code:
- Clean, minimal comments — only where logic is non-obvious
- No unnecessary print statements in loops
- Use numpy vectorized operations instead of Python loops wherever possible
- All three files should work together out of the box when placed in the same folder

---

## TIPS FOR BEST RESULTS

- The more specific you are about your operation, the more realistic the dataset.
  Real column names, real product types, and real cost structures matter.
- If you have actual benchmark numbers (e.g. "our average waste is about 4%,
  our quality pass rate is around 85%"), include them — the AI will build the
  distributions around your real baselines.
- After the AI generates the code, ask it to "add a scenario comparison function
  that runs the generator twice with different configs and prints a side-by-side
  KPI diff" — useful for before/after analysis.
- If you want a Jupyter notebook instead of a plain .py file, just add "format
  the analysis script as a Jupyter notebook with markdown cells explaining each
  section" to the prompt.
