# Printshop Simulator & FloorPlan Decision Engine

A portfolio collection of data-analytics tools for offset print manufacturing, built in Python.
It grew in two phases: a **synthetic trading-card print shop simulator** (dataset generator,
Excel dashboard, ML profit predictor) and **FloorPlan**, a press-room decision engine calibrated
against real monthly production exports.

> **Note on data:** all press identifiers, machine names, and production values in this
> repository are anonymized. Press numbers are fictional and every metric has been perturbed,
> so nothing here reflects any company's actual data.

## What's inside

| Folder | What it is |
|---|---|
| `floorplan/` | **FloorPlan** — a bidirectional press-room decision engine (Streamlit). Answers "my boss needs 10% more sheets — what do I pull?" (backward) and "I fixed the feeder on press 4520 — what did I gain?" (forward). Parses monthly Productivity-by-Machine CSV exports into a 6-press fleet model with per-op-code downtime detail, lever impact math, and a planner. |
| `floorplan/markdowns/` | Full project documentation: architecture, calculation spec, and a decision log (D1–D12). |
| `Calculator/` | The earlier proof-of-concept version of FloorPlan (single-file calculator + Streamlit UI). |
| `Generator/` | Synthetic dataset generator for a trading-card print shop, with a Streamlit "what-if" simulator app and an Excel input dashboard (`simulation_inputs.xlsx`). |
| `Project/` | Generator + ML pipeline packaged together: dataset generation, Excel dashboard, and gross-profit prediction. |
| `train.py` / `predict.py` / `ml/` | XGBoost regressor that predicts job gross profit from inputs available at job-entry time (press, shift, customer, stock, ink config, quantity). |
| `Reports/` | Example outputs: analysis figures and scenario result workbooks. |
| `Explore/` | Ad-hoc calibration explorations. |

## Quick start

**FloorPlan (main app):**
```bash
cd floorplan
pip install -r requirements.txt
streamlit run app.py
```
With no raw CSV exports present it automatically loads `data/snapshot.json`
(six presses × six months of anonymized production data).

**Tests:**
```bash
cd floorplan
python -m pytest tests/test.py -v
```

**Synthetic generator:**
```bash
cd Generator
pip install -r requirements.txt
streamlit run app2.py
```

**ML profit predictor:**
```bash
pip install pandas scikit-learn xgboost joblib
python train.py    # trains on trading_card_print_data.csv
python predict.py  # scores example jobs
```
