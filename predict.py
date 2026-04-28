"""
predict.py — Score a new job before it runs
============================================
Given job inputs available at entry time, predict gross profit.

Usage:
  python predict.py

Or import and call predict_job() directly.
"""

import os
import pandas as pd
import xgboost as xgb
import joblib

# ── PATHS ─────────────────────────────────────────────────────────────────────
script_dir   = os.path.dirname(os.path.abspath(__file__))
model_path   = os.path.join(script_dir, "ml", "models", "gross_profit_model.json")
encoder_path = os.path.join(script_dir, "ml", "models", "encoders.joblib")

# ── LOAD MODEL ────────────────────────────────────────────────────────────────
model    = xgb.XGBRegressor()
model.load_model(model_path)
encoders = joblib.load(encoder_path)

CAT_COLS = ["press", "shift", "customer", "stock_type", "ink_config"]
FEATURES = ["press", "shift", "customer", "stock_type", "ink_config",
            "qty_ordered", "cards_per_sheet"]


def predict_job(press, shift, customer, stock_type, ink_config,
                qty_ordered, cards_per_sheet):
    """
    Predict gross profit for a single job.

    Parameters
    ----------
    press          : str  e.g. "2190"
    shift          : str  e.g. "Red Day"
    customer       : str  e.g. "CUST-A"
    stock_type     : str  e.g. "White" or "Foil"
    ink_config     : str  e.g. "4/4 CMYK"
    qty_ordered    : int  e.g. 40000
    cards_per_sheet: int  e.g. 121

    Returns
    -------
    float: predicted gross profit ($)
    """
    row = {
        "press":           press,
        "shift":           shift,
        "customer":        customer,
        "stock_type":      stock_type,
        "ink_config":      ink_config,
        "qty_ordered":     qty_ordered,
        "cards_per_sheet": cards_per_sheet,
    }
    df = pd.DataFrame([row])

    for col in CAT_COLS:
        le = encoders[col]
        try:
            df[col] = le.transform(df[col].astype(str))
        except ValueError as e:
            raise ValueError(f"Unknown value in '{col}': {e}")

    return float(model.predict(df[FEATURES])[0])


# ── EXAMPLE USAGE ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_jobs = [
        {
            "desc":           "2190 / Day / CUST-A / White / CMYK / 40K",
            "press":          "2190",
            "shift":          "Red Day",
            "customer":       "CUST-A",
            "stock_type":     "White",
            "ink_config":     "4/4 CMYK",
            "qty_ordered":    40000,
            "cards_per_sheet":121,
        },
        {
            "desc":           "2060 / Night / CUST-A / Foil / Foil Stamp / 40K",
            "press":          "2060",
            "shift":          "Black Night",
            "customer":       "CUST-A",
            "stock_type":     "Foil",
            "ink_config":     "4/4 + Foil Stamp",
            "qty_ordered":    40000,
            "cards_per_sheet":100,
        },
        {
            "desc":           "2190 / Day / SPOT / Foil / CMYK / 15K",
            "press":          "2190",
            "shift":          "Red Day",
            "customer":       "SPOT-JOBS",
            "stock_type":     "Foil",
            "ink_config":     "4/4 CMYK",
            "qty_ordered":    15000,
            "cards_per_sheet":121,
        },
    ]

    print(f"\n{'='*60}")
    print(f"GROSS PROFIT PREDICTIONS")
    print(f"{'='*60}")
    for job in test_jobs:
        desc = job.pop("desc")
        profit = predict_job(**job)
        print(f"  {desc}")
        print(f"  → Predicted gross profit: ${profit:,.0f}\n")
