"""
train.py — Print Shop Gross Profit Predictor
=============================================
Predicts gross_profit for a job before it runs using only
inputs available at job entry time.

Features:  press, shift, customer, stock_type, ink_config,
           qty_ordered, cards_per_sheet
Target:    gross_profit ($)

Run:  python train.py
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
import joblib

# ── PATHS ─────────────────────────────────────────────────────────────────────
script_dir  = os.path.dirname(os.path.abspath(__file__))
data_path   = os.path.join(script_dir, "trading_card_print_data.csv")
model_dir   = os.path.join(script_dir, "ml", "models")
os.makedirs(model_dir, exist_ok=True)

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
print("Loading data...")
df = pd.read_csv(data_path)
print(f"  Rows: {len(df)}")

# ── FEATURES ──────────────────────────────────────────────────────────────────
# Only use columns available before a job runs
FEATURES = [
    "press",
    "shift",
    "customer",
    "stock_type",
    "ink_config",
    "qty_ordered",
    "cards_per_sheet",
]
TARGET = "gross_profit"

X = df[FEATURES].copy()
y = df[TARGET].copy()

# ── ENCODE CATEGORICALS ───────────────────────────────────────────────────────
CAT_COLS = ["press", "shift", "customer", "stock_type", "ink_config"]
encoders = {}

for col in CAT_COLS:
    le = LabelEncoder()
    X[col] = le.fit_transform(X[col].astype(str))
    encoders[col] = le
    print(f"  Encoded {col}: {list(le.classes_)}")

# ── TRAIN / TEST SPLIT ────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"\nTrain: {len(X_train)} rows  |  Test: {len(X_test)} rows")

# ── TRAIN MODEL ───────────────────────────────────────────────────────────────
print("\nTraining XGBoost regressor...")
model = xgb.XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbosity=0,
)
model.fit(X_train, y_train)

# ── EVALUATE ──────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
rmse   = np.sqrt(mean_squared_error(y_test, y_pred))
r2     = r2_score(y_test, y_pred)

print(f"\n{'='*50}")
print(f"MODEL PERFORMANCE")
print(f"{'='*50}")
print(f"  RMSE:  ${rmse:,.0f}")
print(f"  R²:    {r2:.4f}")
print(f"  Avg actual profit:    ${y_test.mean():,.0f}")
print(f"  Avg predicted profit: ${y_pred.mean():,.0f}")

# ── FEATURE IMPORTANCE ────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"FEATURE IMPORTANCE")
print(f"{'='*50}")
importance = pd.Series(model.feature_importances_, index=FEATURES)
importance = importance.sort_values(ascending=False)
for feat, score in importance.items():
    bar = "█" * int(score * 50)
    print(f"  {feat:<20} {score:.4f}  {bar}")

# ── SAVE MODEL ────────────────────────────────────────────────────────────────
model_path   = os.path.join(model_dir, "gross_profit_model.json")
encoder_path = os.path.join(model_dir, "encoders.joblib")

model.save_model(model_path)
joblib.dump(encoders, encoder_path)

print(f"\n{'='*50}")
print(f"SAVED")
print(f"{'='*50}")
print(f"  Model:    {model_path}")
print(f"  Encoders: {encoder_path}")
print(f"\nTo predict on new jobs, run: python predict.py")
