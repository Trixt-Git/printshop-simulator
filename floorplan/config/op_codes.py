"""
config/op_codes.py

Single source of truth for operation code → category mapping.
If a code's categorization changes, edit only this file.

Source: decisions.md D3 — categorization validated against real CSV data
(May 2026). Supersedes the original handoff mapping.
"""

# ---------------------------------------------------------------------------
# Lever categories — controllable downtime
# Keys match Press.downtime_by_lever
# ---------------------------------------------------------------------------

LEVERS = {
    "maintenance":    ["2011", "2000", "2001", "2088", "1050"],
    "jams":           ["2070", "2085", "2086", "2087", "2097", "2078"],
    "shift_handoff":  ["2040", "2041", "2089"],
    "materials_wait": ["2090", "2095", "2096"],
    "quality_wait":   ["2120", "2123", "2081"],
    "approval_wait":  ["2080", "2121", "2122", "2124", "2125"],
    "makeready":      ["1000", "1010", "1060", "2075", "2076", "2082", "2083", "2084", "2021", "2079"],
}

# Flat set of all lever op codes — used by parser to route rows into levers
LEVER_CODE_TO_CATEGORY = {
    code: category
    for category, codes in LEVERS.items()
    for code in codes
}

# ---------------------------------------------------------------------------
# Productive operations — not downtime, drives sheet counts and run hours
# ---------------------------------------------------------------------------

PRODUCTIVE = {
    "run":      "1020",   # actual run time — net/gross sheets come from here
    "over_run": "1030",
}

# ---------------------------------------------------------------------------
# Excluded codes — subtracted from available hours or acknowledged but not modeled
# ---------------------------------------------------------------------------

EXCLUDED = {
    "no_crew":        "2060",           # subtracted from available_hrs
    "planned_maint":  "2010",           # subtracted from available_hrs
    "breaks":         "2030",           # acknowledged, not modeled
    "training":       ["2050", "2118"], # acknowledged, not modeled
}

# ---------------------------------------------------------------------------
# Machine name → press ID
# Used by the CSV parser to identify which press each row belongs to
# ---------------------------------------------------------------------------

MACHINE_MAP = {
    "B2-50101  -  B2-4080 KBA105-PCUV-Sheetfed":    "4080",
    "B2-50102  -  B2-4210 KBA106-PCUV-Sheetfed":    "4210",
    "B2-50103  -  B2-4180_840 Komori-CUV Sheefed":  "4180",
    "B2-50104  -  B2-4520_640 Komori-C Sheetfed":   "4520",
    "B2-50106  -  B2-4360_640 Komori-C Sheetfed":   "4360",
    "B2-50107  -  B2-4140_640 Komori-CUV Sheetfed": "4140",
}
