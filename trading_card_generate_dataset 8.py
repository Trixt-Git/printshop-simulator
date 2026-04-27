import pandas as pd
import numpy as np
import os, sys, random
from datetime import datetime, timedelta

# 1.1 — DYNAMIC PATHING
script_dir = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(script_dir, "simulation_inputs.xlsx")

# 1.2 — ROBUST INGESTION
try:
    df_front = pd.read_excel(excel_path, sheet_name="Main Control Panel", header=None)
    df_back  = pd.read_excel(excel_path, sheet_name="Backend Engine", header=None)
    df_all   = pd.concat([df_front, df_back])
    xl_conf  = {str(row[0]).strip(): row[1] for _, row in df_all.iterrows()}
except Exception as e:
    print(f"❌ Excel Sync Error: {e}")
    sys.exit(1)

# 1.3 — GLOBAL CONFIG
RANDOM_SEED     = int(xl_conf.get("RANDOM_SEED", 42))
START_DATE_STR  = str(xl_conf.get("START_DATE", "2022-01-01")).split(" ")[0]
DATE_RANGE_DAYS = int(xl_conf.get("DATE_RANGE_DAYS", 730))

# 2.1 — SHIFT MIX
SHIFTS = {
    "Red Day":    xl_conf.get("SHIFT_MIX_RED_DAY",   0.25),
    "Red Night":  xl_conf.get("SHIFT_MIX_RED_NIGHT", 0.25),
    "Black Day":  xl_conf.get("SHIFT_MIX_BLACK_DAY", 0.25),
    "Black Night":xl_conf.get("SHIFT_MIX_BLACK_NIGHT",0.25),
}

# 2.2 — LAYOUT & STOCK (121-up or 100-up, each available in White or Foil)
LAYOUT_MIX = {
    (121, "White"): xl_conf.get("MIX_121_PLAIN", 0.40),
    (121, "Foil"):  xl_conf.get("MIX_121_HOLO",  0.25),
    (100, "White"): xl_conf.get("MIX_100_PLAIN", 0.15),
    (100, "Foil"):  xl_conf.get("MIX_100_HOLO",  0.20),
}

# 3.1 — WASTE BASE (Stock, Ink Config)
WASTE_BASE = {
    ("White", "4/4 CMYK"):        0.025,
    ("White", "4/4 + Spot Gloss"): 0.038,
    ("White", "4/4 + Foil Stamp"): 0.045,
    ("White", "4/4 + Spot UV"):    0.038,
    ("Foil",  "4/4 CMYK"):        0.055,
    ("Foil",  "4/4 + Spot Gloss"): 0.060,
    ("Foil",  "4/4 + Foil Stamp"): 0.065,
    ("Foil",  "4/4 + Spot UV"):    0.060,
}

# 3.2 — FINANCIALS (hardcoded matrices)
PLATE_COSTS = {
    "4/4 CMYK":        260,
    "4/4 + Spot Gloss": 380,
    "4/4 + Foil Stamp": 520,
    "4/4 + Spot UV":    380,
}
FINISHING_PER_SHEET = {
    "4/4 CMYK":        0.000,
    "4/4 + Spot Gloss": 0.009,
    "4/4 + Foil Stamp": 0.018,
    "4/4 + Spot UV":    0.009,
}
QTY_OPTIONS = [15000, 25000, 40000, 60000, 100000]

def normalize(p): return np.array(p) / np.sum(p)


def generate_dataset(overrides=None):
    conf = {**xl_conf, **(overrides or {})}

    # ── PRESS FLEET (rebuilt each call so overrides take effect) ─────────
    press_fleet = {
        "2190": ("Perfecting", conf.get("SHARE_2190", 0.30), conf.get("AGE_FACTOR_2190", 1.15)),
        "2160": ("Sheetfed",   conf.get("SHARE_2160", 0.21), conf.get("AGE_FACTOR_2160", 1.30)),
        "2150": ("Sheetfed",   conf.get("SHARE_2150", 0.19), conf.get("AGE_FACTOR_2150", 1.25)),
        "2500": ("Sheetfed",   conf.get("SHARE_2500", 0.16), conf.get("AGE_FACTOR_2500", 1.20)),
        "2330": ("Sheetfed",   conf.get("SHARE_2330", 0.08), conf.get("AGE_FACTOR_2330", 1.20)),
        "2060": ("Perfecting", conf.get("SHARE_2060", 0.06), conf.get("AGE_FACTOR_2060", 1.50)),
    }

    n = int(conf.get("NUM_JOBS", 5000))
    np.random.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    # 4.1 — SAMPLING
    selected_shifts = np.random.choice(
        list(SHIFTS.keys()), n, p=normalize(list(SHIFTS.values()))
    )

    c_ids = ["CUST-A", "CUST-B", "SPOT-JOBS"]
    c_p   = [conf.get("CUST_A_SHARE", 0.7),
             conf.get("CUST_B_SHARE",  0.2),
             conf.get("SPOT_JOB_SHARE",0.1)]
    selected_custs = np.random.choice(c_ids, n, p=normalize(c_p))

    layouts = list(LAYOUT_MIX.keys())
    idx = np.random.choice(len(layouts), n, p=normalize(list(LAYOUT_MIX.values())))
    cards_per_sheet = np.array([layouts[i][0] for i in idx])
    stock_type      = np.array([layouts[i][1] for i in idx])

    press_names    = list(press_fleet.keys())
    selected_presses = np.random.choice(
        press_names, n, p=normalize([v[1] for v in press_fleet.values()])
    )

    # 4.2 — PHYSICS MAPPING
    press_age     = np.array([press_fleet[p][2] for p in selected_presses])
    is_night      = np.array(["Night" in s for s in selected_shifts])
    is_foil       = (stock_type == "Foil")
    is_perfecting = np.array([press_fleet[p][0] == "Perfecting" for p in selected_presses])

    ink_configs  = list(PLATE_COSTS.keys())
    ink_weights  = normalize([0.45, 0.25, 0.15, 0.15])
    ink_config   = np.random.choice(ink_configs, n, p=ink_weights)
    qty_ordered  = np.random.choice(QTY_OPTIONS, n)

    # 4.3 — WASTE: continuous drift (age + shift + substrate)
    night_w_mult   = np.where(is_night, conf.get("NIGHT_WASTE_FACTOR", 1.15), 1.0)
    foil_w_mult    = np.where(is_foil,  conf.get("FOIL_WASTE_FACTOR",  1.25), 1.0)
    base_run_waste = np.array([WASTE_BASE.get((s, c), 0.04)
                               for s, c in zip(stock_type, ink_config)])
    run_waste_pct  = base_run_waste * press_age * night_w_mult * foil_w_mult
    mkrdy_scrap    = int(conf.get("MAKEREADY_ATTEMPTS", 5) * conf.get("SHEETS_PER_ATTEMPT", 50))
    run_scrap      = (qty_ordered * run_waste_pct).astype(int)

    # 4.3b — 5-POINT QC SYSTEM
    night_q_mult   = np.where(is_night, conf.get("NIGHT_QUALITY_FACTOR", 1.15), 1.0)
    drift          = press_age * night_q_mult
    delta_e_base   = np.where(is_foil, 1.0, 0.65)
    register_base  = np.where(is_foil, 0.5, 0.3)

    color_delta_e    = (np.random.exponential(delta_e_base, n) * drift).clip(0.1, 9.0).round(2)
    register_error   = (np.random.exponential(register_base, n) * drift).clip(0.0, 5.0).round(3)
    dot_gain_pct     = (np.random.normal(21, 3, n) * night_q_mult).clip(10, 38).round(1)
    cut_deviation_mm = (np.random.exponential(0.12, n) * drift).clip(0.0, 1.5).round(3)
    foil_adhesion    = np.where(is_foil, np.random.normal(88, 8, n).clip(40, 100), np.nan)

    quality_pass = (
        (color_delta_e    < conf.get("DELTA_E_REJECT",       3.5)) &
        (register_error   < conf.get("REGISTER_REJECT",      2.0)) &
        (dot_gain_pct     < conf.get("DOT_GAIN_REJECT",     30.0)) &
        (cut_deviation_mm < conf.get("CUT_DEVIATION_REJECT", 0.5))
    ).astype(int)
    quality_pass = np.where(
        is_foil & (foil_adhesion < conf.get("FOIL_ADHESION_FAIL", 70)), 0, quality_pass
    )

    qc_scrap        = np.where(quality_pass == 0, int(conf.get("DEFECT_WINDOW_SHEETS", 50)), 0)
    qc_downtime_hrs = np.where(quality_pass == 0, conf.get("QC_READJUST_MINUTES", 15) / 60, 0)

    # 4.3c — JAM MODEL: discrete mechanical events (run length + age + foil)
    jam_lambda   = (conf.get("JAM_RATE_PER_10K_SHEETS", 0.03)
                    * (qty_ordered / 10000.0)
                    * press_age
                    * np.where(is_foil, conf.get("FOIL_WASTE_FACTOR", 1.25), 1.0))
    jam_count    = np.random.poisson(jam_lambda, n)
    jam_waste    = jam_count * int(conf.get("JAM_WASTE_SHEETS", 30))
    jam_time_hrs = jam_count * conf.get("JAM_MINUTES", 20) / 60

    sheets_run = qty_ordered + mkrdy_scrap + run_scrap + qc_scrap + jam_waste

    # 4.4 — SPEED & TIME
    passes     = np.where(is_perfecting, 1, 2)
    speed_base = np.where(is_foil & is_perfecting, conf.get("BASE_SPEED_FOIL_PERFECTING", 6500),
                 np.where(is_foil,                 conf.get("BASE_SPEED_FOIL_SHEETFED",   7500),
                 np.where(is_perfecting,            conf.get("BASE_SPEED_WHITE_PERFECTING",9500),
                                                    conf.get("BASE_SPEED_WHITE_SHEETFED", 10500))))

    act_speed  = (speed_base / press_age) + np.random.normal(0, conf.get("SPEED_NOISE_STD", 400), n)

    mkrdy_base = np.random.normal(90, conf.get("MAKEREADY_NOISE_STD", 12), n)
    mkrdy_time = np.where(is_perfecting,
                          mkrdy_base * conf.get("PERFECTING_MAKEREADY_BONUS", 0.8),
                          mkrdy_base)
    mkrdy_time = np.where(is_foil, mkrdy_time * conf.get("FOIL_MAKEREADY_FACTOR", 1.25), mkrdy_time)

    run_time   = (sheets_run * passes / act_speed).round(2)
    total_time = ((mkrdy_time / 60) + run_time + jam_time_hrs + qc_downtime_hrs).round(2)

    # 4.5 — FINANCIALS
    paper_cost = (sheets_run * np.where(is_foil,
                  conf.get("STOCK_COST_FOIL",  320) / 1000,
                  conf.get("STOCK_COST_WHITE",  55) / 1000)).round(2)

    cov        = np.random.uniform(conf.get("INK_COVERAGE_MIN", 0.55),
                                   conf.get("INK_COVERAGE_MAX", 0.90), n)
    ink_premium = np.where(np.char.find(ink_config, "4/4 CMYK") > -1, 1.0, 1.6)
    ink_yield   = conf.get("INK_YIELD_SHEETS_PER_LB", 50000)
    ink_cost    = (sheets_run * cov * 4 / ink_yield
                   * conf.get("INK_COST_PER_LB", 20) * ink_premium).round(2)

    # Cost rate — what it actually costs to run the press
    base_cost_rate = np.where(is_perfecting,
                              conf.get("PERFECTING_RATE_HR",    150),
                              conf.get("SHEETFED_RATE_HR",      140))
    burden_rate = conf.get("BURDEN_RATE_HR", 0)
    labor_rate  = np.where(is_night, base_cost_rate + burden_rate + 4.0,
                                     base_cost_rate + burden_rate)
    press_cost  = (total_time * labor_rate).round(2)

    # Billing rate — what we charge the customer
    base_bill_rate = np.where(is_perfecting,
                               conf.get("PERFECTING_BILL_RATE_HR", 285),
                               conf.get("SHEETFED_BILL_RATE_HR",   250))
    bill_rate = np.where(is_night, base_bill_rate + 4.0, base_bill_rate)

    plt_c = np.array([PLATE_COSTS[c] for c in ink_config])
    fin_c = (sheets_run * np.array([FINISHING_PER_SHEET[c] for c in ink_config])).round(2)

    total_cost = (paper_cost + ink_cost + press_cost + plt_c + fin_c).round(2)

    # Markup
    markups_dict = {
        "CUST-A":    conf.get("CUST_A_MARKUP",       1.25),
        "CUST-B":    conf.get("CUST_B_MARKUP",       1.40),
        "SPOT-JOBS": conf.get("SPOT_MARKUP_PREMIUM", 1.55),
    }
    job_markup = np.array([markups_dict[c] for c in selected_custs])
    job_markup = np.where(is_foil, job_markup + conf.get("COMPLEXITY_PREMIUM_FOIL", 0.15), job_markup)

    # Billing basis: revenue on what the customer ordered, not actual sheets run
    # Waste, jams, and QC hits eat margin — the shop absorbs them
    # Uses std_speed (no age degradation) — age slowdowns are the shop's problem
    std_speed = np.where(is_foil & is_perfecting, conf.get("BASE_SPEED_FOIL_PERFECTING", 6500),
                np.where(is_foil,                 conf.get("BASE_SPEED_FOIL_SHEETFED",   7500),
                np.where(is_perfecting,            conf.get("BASE_SPEED_WHITE_PERFECTING",9500),
                                                   conf.get("BASE_SPEED_WHITE_SHEETFED", 10500))))

    billing_basis = (
        qty_ordered * np.where(is_foil,
                               conf.get("STOCK_COST_FOIL",  320) / 1000,
                               conf.get("STOCK_COST_WHITE",  55) / 1000)
        + qty_ordered * cov * 4 / ink_yield * conf.get("INK_COST_PER_LB", 20) * ink_premium
        + (qty_ordered * passes / std_speed + mkrdy_time / 60) * bill_rate
        + plt_c
        + qty_ordered * np.array([FINISHING_PER_SHEET[c] for c in ink_config])
    ).round(2)

    revenue = (billing_basis * job_markup).round(2)

    # 4.6 — DELIVERY: derived from actual press time
    quoted = np.random.normal(
        conf.get("LEAD_TIME_MEAN_DAYS", 8),
        conf.get("LEAD_TIME_STD_DAYS",  2), n
    ).astype(int).clip(3, 15)

    press_days     = total_time / conf.get("DELIVERY_HOURS_PER_DAY", 24.0)
    delivery_noise = np.random.normal(0, conf.get("ACTUAL_TIME_STD", 0.75), n)
    actual         = (conf.get("DELIVERY_BASE_DAYS", 6) + press_days + delivery_noise).astype(int).clip(3, 30)
    delivery_status = np.where(actual > quoted, "LATE", "ON-TIME")

    return pd.DataFrame({
        "job_id":           [f"JOB-{i:05d}" for i in range(n)],
        "job_date":         [(datetime.strptime(START_DATE_STR, "%Y-%m-%d")
                              + timedelta(days=int(d))).strftime("%Y-%m-%d")
                             for d in np.sort(np.random.randint(0, DATE_RANGE_DAYS, n))],
        "customer":         selected_custs,
        "press":            selected_presses,
        "shift":            selected_shifts,
        "stock_type":       stock_type,
        "ink_config":       ink_config,
        "cards_per_sheet":  cards_per_sheet,
        "qty_ordered":      qty_ordered,
        "passes":           passes,
        "sheets_run":       sheets_run,
        "cards_delivered":  sheets_run * cards_per_sheet,
        "waste_pct":        (((sheets_run - qty_ordered) / sheets_run) * 100).round(2),
        "color_delta_e":    color_delta_e,
        "register_error":   register_error,
        "dot_gain_pct":     dot_gain_pct,
        "cut_deviation_mm": cut_deviation_mm,
        "foil_adhesion":    foil_adhesion,
        "quality_pass":     quality_pass,
        "jam_count":        jam_count,
        "total_press_time": total_time,
        "paper_cost":       paper_cost,
        "press_cost":       press_cost,
        "ink_cost":         ink_cost,
        "plate_cost":       plt_c,
        "finishing_cost":   fin_c,
        "total_cost":       total_cost,
        "revenue":          revenue,
        "gross_profit":     (revenue - total_cost).round(2),
        "gross_margin_pct": ((revenue - total_cost) / revenue * 100).round(1),
        "delivery_quoted":  quoted,
        "delivery_actual":  actual,
        "delivery_status":  delivery_status,
    })


if __name__ == "__main__":
    df = generate_dataset()
    csv_path = os.path.join(script_dir, "trading_card_print_data.csv")
    df.to_csv(csv_path, index=False)

    print("--- 🔬 V9.0 Engine Validation ---")
    print(f"✅ Variables Mapped:  {len(xl_conf)}")
    print(f"✅ Data Rows:         {len(df)}")
    print(f"✅ Cust A Share:      {df['customer'].value_counts(normalize=True)['CUST-A']:.1%}")
    print(f"✅ Avg Margin:        {df['gross_margin_pct'].mean():.2f}%")
    print(f"✅ QC Fail Rate:      {(1 - df['quality_pass'].mean()):.1%}")
    print(f"✅ Late Rate:         {(df['delivery_status']=='LATE').mean():.1%}")
    print(f"✅ Avg Jams/Job:      {df['jam_count'].mean():.3f}")
    print(f"✅ Dataset Saved:     {csv_path}")
