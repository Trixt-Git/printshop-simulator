# Trading Card Print Shop — Analysis Toolkit

A synthetic dataset generator and analysis suite for offset trading card manufacturing. Built for portfolio projects, scenario modeling, and press/shift optimization analysis.

---

## Files

| File | Description |
|---|---|
| `trading_card_generate_dataset.py` | Generates the synthetic dataset (CSV + Excel) |
| `trading_card_analysis.py` | Runs analysis and produces 6 charts |
| `trading_card_print_data.csv` | Pre-generated dataset (1,000 jobs) |
| `trading_card_print_data.xlsx` | Same dataset formatted in Excel with a summary dashboard |

---

## Quick Start

**Install dependencies**
```bash
pip install pandas numpy matplotlib openpyxl
```

**Generate a fresh dataset**
```bash
python trading_card_generate_dataset.py
```

**Run the analysis**
```bash
python trading_card_analysis.py
```

Both scripts expect to be run from the same folder as the CSV file.

---

## Dataset Overview

1,000 simulated print jobs across a 2-year period. Each row is one job.

**41 columns covering:**
- Job metadata — date, customer, card set, shift, press
- Press specs — type (sheetfed/perfecting), passes required, speed
- Stock — White or Foil
- Ink config — 4/4 CMYK, + Spot Gloss, + Foil Stamp, + Spot UV
- Production metrics — makeready time, run time, waste %, press speed
- Quality metrics — color delta E, register error, dot gain, cut deviation, foil adhesion
- Financials — paper cost, press cost, ink cost, plates, finishing, revenue, margin
- Outcome — quality pass/fail, rerun required, on-time delivery

**5 presses:**
- SF-1, SF-2, SF-3 — Sheetfed (4/4 requires 2 passes)
- PF-1, PF-2 — Perfecting (prints both sides in 1 pass)
- SF-3 and PF-2 are modeled as older/lower-performing presses

**4 shifts:**
- Red Day, Red Night, Black Day, Black Night
- Night shifts carry a small waste and quality penalty
- Any press can be used by any shift

---

## Scenario Modeling

All configurable variables live in the `CONFIG` block at the top of `trading_card_generate_dataset.py`. Change values there and re-run — no other edits needed.

**Common scenarios:**

**Simulate a press upgrade**
Lower `age_factor` on SF-3 or PF-2 from `1.2` to `1.0`:
```python
PRESSES = {
    ...
    "SF-3": ("Sheetfed", 0.18, 1.0),  # upgraded — was 1.2
    ...
}
```

**Change stock mix**
Increase foil share to model a product line shift:
```python
STOCK_MIX = {
    "White": 0.50,
    "Foil":  0.50,  # up from 0.35
}
```

**Model night shift improvements**
Reduce the night penalty to simulate better training or supervision:
```python
NIGHT_WASTE_FACTOR   = 1.05  # down from 1.15
NIGHT_QUALITY_FACTOR = 1.05
```

**Stress test high volume**
```python
NUM_JOBS        = 5000
DATE_RANGE_DAYS = 365  # same volume in half the time
```

**Add a press**
Add an entry to `PRESSES` and redistribute `job_share` so values sum to 1.0:
```python
PRESSES = {
    "SF-1": ("Sheetfed",   0.18, 1.0),
    "SF-2": ("Sheetfed",   0.18, 1.0),
    "SF-3": ("Sheetfed",   0.16, 1.2),
    "PF-1": ("Perfecting", 0.18, 1.0),
    "PF-2": ("Perfecting", 0.16, 1.2),
    "PF-3": ("Perfecting", 0.14, 1.0),  # new press
}
```

---

## Analysis Charts

Running `trading_card_analysis.py` produces 6 PNG files:

| File | What it shows |
|---|---|
| `fig1_cost_drivers.png` | Average cost breakdown per job — White vs Foil |
| `fig2_press_performance.png` | Waste %, quality pass rate, makeready time by press |
| `fig3_shift_analysis.png` | Waste %, quality pass rate, rerun rate by shift |
| `fig4_foil_vs_white.png` | Gross margin, cost per card, rerun rate by stock type |
| `fig5_waste_heatmap.png` | Waste % heatmap — every press × shift combination |
| `fig6_rerun_cost.png` | Total dollar cost of reruns by press and by shift |

---

## Portfolio Project Ideas

These are analysis angles that would resonate with a manufacturing or finance employer:

- **Press ROI analysis** — model the cost of SF-3/PF-2 underperformance vs. the cost of replacement
- **Shift efficiency report** — quantify the dollar impact of the night shift waste premium
- **Foil profitability deep dive** — foil has higher revenue per card but also higher rerun risk; find the breakeven
- **Predictive quality model** — use `makeready_time_min`, `press`, `shift`, and `stock_type` to predict `quality_pass`
- **Capacity optimization** — given 5 presses and 4 shifts, which job types should be routed to which press?
