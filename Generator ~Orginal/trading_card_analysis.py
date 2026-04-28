"""
Trading Card Print Shop — Production Analysis
=============================================
Requires: pandas, numpy, matplotlib
Run with: python trading_card_analysis.py

Expects 'trading_card_print_data.csv' in the same directory.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import warnings
warnings.filterwarnings("ignore")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CSV_FILE = "trading_card_print_data.csv"

BLUE   = "#1F4E79"
MED    = "#2E75B6"
LIGHT  = "#BDD7EE"
RED    = "#C00000"
ORANGE = "#ED7D31"
GREEN  = "#375623"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.facecolor": "#FAFAFA",
    "figure.facecolor": "white",
})

# ── LOAD DATA ──────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_FILE)
print(f"Loaded {len(df):,} jobs | Columns: {df.shape[1]}")

# ── SUMMARY STATS ──────────────────────────────────────────────────────────────
print("\n=== KEY FINDINGS ===")
print(f"Total revenue:          ${df['revenue'].sum():>12,.0f}")
print(f"Total gross profit:     ${df['gross_profit'].sum():>12,.0f}")
print(f"Avg gross margin:       {df['gross_margin_pct'].mean():>11.1f}%")
print(f"Quality pass rate:      {df['quality_pass'].mean():>11.1%}")
print(f"Rerun rate:             {df['rerun_required'].mean():>11.1%}")
print(f"Total rerun cost:       ${df[df['rerun_required']==1]['total_cost'].sum():>12,.0f}")
print(f"Night shift waste premium: {df[df['shift'].str.contains('Night')]['waste_pct'].mean() - df[df['shift'].str.contains('Day')]['waste_pct'].mean():.2f}%")

print("\n--- Press Summary ---")
print(df.groupby(["press","press_type"])[["waste_pct","quality_pass","makeready_time_min","gross_margin_pct"]].mean().round(2))

print("\n--- Shift Summary ---")
print(df.groupby("shift")[["waste_pct","quality_pass","rerun_required"]].mean().round(3))

print("\n--- Stock Type Summary ---")
print(df.groupby("stock_type")[["waste_pct","quality_pass","cost_per_card","gross_margin_pct"]].mean().round(3))


# ── CHART 1: COST DRIVERS BY STOCK TYPE ───────────────────────────────────────
fig1, axes = plt.subplots(1, 2, figsize=(14, 5))
fig1.suptitle("Cost Driver Analysis — Trading Card Print Shop",
              fontsize=14, fontweight="bold", color=BLUE)

cost_cols   = ["paper_cost", "press_cost", "ink_cost", "plate_cost", "finishing_cost"]
cost_labels = ["Paper/Foil", "Press Time", "Ink", "Plates", "Finishing"]

for ax, stock, color in zip(axes, ["White", "Foil"], [MED, RED]):
    sub    = df[df["stock_type"] == stock]
    totals = [sub[c].mean() for c in cost_cols]
    bars   = ax.barh(cost_labels, totals, color=color, edgecolor="white")
    ax.set_title(f"{stock} Stock — Avg Cost per Job", fontweight="bold", color=BLUE)
    ax.set_xlabel("Avg Cost ($)")
    for bar, val in zip(bars, totals):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height() / 2,
                f"${val:,.0f}", va="center", fontsize=9)
    ax.set_xlim(0, max(totals) * 1.28)

plt.tight_layout()
plt.savefig("fig1_cost_drivers.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig1_cost_drivers.png")


# ── CHART 2: PRESS PERFORMANCE ────────────────────────────────────────────────
fig2, axes = plt.subplots(1, 3, figsize=(15, 5))
fig2.suptitle("Press Performance Comparison", fontsize=14, fontweight="bold", color=BLUE)

presses       = ["SF-1", "SF-2", "SF-3", "PF-1", "PF-2"]
press_colors  = [MED, MED, ORANGE, GREEN, ORANGE]

for (col, title, ax) in [
    ("waste_pct",          "Avg Waste %",          axes[0]),
    ("quality_pass",       "Quality Pass Rate",     axes[1]),
    ("makeready_time_min", "Avg Makeready (min)",   axes[2]),
]:
    vals = [df[df["press"] == p][col].mean() for p in presses]
    bars = ax.bar(presses, vals, color=press_colors, edgecolor="white", width=0.6)
    ax.set_title(title, fontweight="bold", color=BLUE)
    xlabels = [f"{p}\n{'Sheetfed' if 'SF' in p else 'Perfecting'}" for p in presses]
    ax.set_xticklabels(xlabels, fontsize=8)
    for bar, val in zip(bars, vals):
        label = f"{val:.1f}" if val > 1 else f"{val:.0%}"
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.015,
                label, ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("fig2_press_performance.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig2_press_performance.png")


# ── CHART 3: SHIFT ANALYSIS ───────────────────────────────────────────────────
fig3, axes = plt.subplots(1, 3, figsize=(15, 5))
fig3.suptitle("Shift Performance Analysis", fontsize=14, fontweight="bold", color=BLUE)

shifts        = ["Red Day", "Red Night", "Black Day", "Black Night"]
shift_colors  = ["#C00000", "#FF9999", "#1F4E79", "#6FA8DC"]

for (col, title, fmt), ax in zip([
    ("waste_pct",       "Avg Waste %",      "{:.1f}"),
    ("quality_pass",    "Quality Pass Rate", "{:.1%}"),
    ("rerun_required",  "Rerun Rate",        "{:.1%}"),
], axes):
    vals = [df[df["shift"] == s][col].mean() for s in shifts]
    bars = ax.bar(shifts, vals, color=shift_colors, edgecolor="white", width=0.6)
    ax.set_title(title, fontweight="bold", color=BLUE)
    ax.set_xticklabels(shifts, rotation=20, ha="right", fontsize=9)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.015,
                fmt.format(val), ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("fig3_shift_analysis.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig3_shift_analysis.png")


# ── CHART 4: WHITE vs FOIL FINANCIAL PROFILE ──────────────────────────────────
fig4, axes = plt.subplots(1, 3, figsize=(15, 5))
fig4.suptitle("White vs Foil — Financial & Quality Profile",
              fontsize=14, fontweight="bold", color=BLUE)

for (col, title, fmt), ax in zip([
    ("gross_margin_pct", "Avg Gross Margin %",    "{:.1f}%"),
    ("cost_per_card",    "Avg Cost per Card ($)",  "${:.4f}"),
    ("rerun_required",   "Rerun Rate",             "{:.1%}"),
], axes):
    vals = [df[df["stock_type"] == s][col].mean() for s in ["White", "Foil"]]
    bars = ax.bar(["White", "Foil"], vals, color=[MED, RED], edgecolor="white", width=0.5)
    ax.set_title(title, fontweight="bold", color=BLUE)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.015,
                fmt.format(val), ha="center", fontsize=10, fontweight="bold")

plt.tight_layout()
plt.savefig("fig4_foil_vs_white.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig4_foil_vs_white.png")


# ── CHART 5: WASTE HEATMAP — PRESS × SHIFT ────────────────────────────────────
fig5, ax = plt.subplots(figsize=(10, 5))
fig5.suptitle("Waste % Heatmap — Press × Shift",
              fontsize=14, fontweight="bold", color=BLUE)

pivot = df.pivot_table(values="waste_pct", index="press", columns="shift", aggfunc="mean")
pivot = pivot[["Red Day", "Red Night", "Black Day", "Black Night"]]
pivot = pivot.reindex(["SF-1", "SF-2", "SF-3", "PF-1", "PF-2"])

cmap = LinearSegmentedColormap.from_list("rg", ["#375623", "#FFEB84", "#C00000"])
im   = ax.imshow(pivot.values, cmap=cmap, aspect="auto")
plt.colorbar(im, ax=ax, label="Avg Waste %")

ax.set_xticks(range(4));  ax.set_xticklabels(pivot.columns, fontsize=10)
ax.set_yticks(range(5));  ax.set_yticklabels(pivot.index, fontsize=10)

for i in range(5):
    for j in range(4):
        val = pivot.values[i, j]
        ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                fontsize=11, fontweight="bold",
                color="white" if val > pivot.values.mean() else "black")

plt.tight_layout()
plt.savefig("fig5_waste_heatmap.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig5_waste_heatmap.png")


# ── CHART 6: RERUN COST IMPACT ────────────────────────────────────────────────
fig6, axes = plt.subplots(1, 2, figsize=(14, 5))
fig6.suptitle("Rerun Cost Impact", fontsize=14, fontweight="bold", color=BLUE)

rerun = df[df["rerun_required"] == 1]

rerun_press = rerun.groupby("press")["total_cost"].sum()
bars = axes[0].bar(rerun_press.index, rerun_press.values,
                   color=[MED, MED, RED, GREEN, ORANGE], edgecolor="white")
axes[0].set_title("Total Rerun Cost by Press", fontweight="bold", color=BLUE)
axes[0].set_ylabel("Total Rerun Cost ($)")
for bar, val in zip(bars, rerun_press.values):
    axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
                 f"${val:,.0f}", ha="center", fontsize=9)

rerun_shift = rerun.groupby("shift")["total_cost"].sum().reindex(shifts)
bars2 = axes[1].bar(rerun_shift.index, rerun_shift.values,
                    color=shift_colors, edgecolor="white")
axes[1].set_title("Total Rerun Cost by Shift", fontweight="bold", color=BLUE)
axes[1].set_ylabel("Total Rerun Cost ($)")
axes[1].set_xticklabels(shifts, rotation=20, ha="right")
for bar, val in zip(bars2, rerun_shift.values):
    axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
                 f"${val:,.0f}", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("fig6_rerun_cost.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: fig6_rerun_cost.png")

print("\nAnalysis complete. Keep this script in the same folder as the CSV.")
