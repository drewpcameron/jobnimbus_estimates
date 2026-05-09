"""
Converts roof measurements into a line-item roofing estimate.
Linear footage items use industry rules of thumb scaled by complexity tier.
"""

import math
from measurement_engine import measure


# ── Pricing constants ─────────────────────────────────────────────────────────

SHINGLE_PER_SQUARE      = 135.00
LABOR_PER_SQUARE        = 175.00
UNDERLAYMENT_PER_SQ     = 25.00
ICE_WATER_PER_SQ        = 75.00
RIDGE_CAP_PER_LF        = 5.00
HIP_CAP_PER_LF          = 5.00
VALLEY_PER_LF           = 7.00
RAKE_PER_LF             = 2.50
EAVE_DRIP_PER_LF        = 2.00
FLASHING_PER_LF         = 9.00
STEP_FLASHING_PER_LF    = 10.00
DUMP_FEE                = 350.00
OVERHEAD_PROFIT         = 0.20

PITCH_MULTIPLIERS = [
    (0,  14,  1.00),
    (15, 18,  1.06),
    (19, 23,  1.12),
    (24, 27,  1.20),
    (28, 31,  1.30),
    (32, 36,  1.41),
    (37, 90,  1.54),
]

# Linear footage multipliers per net square, by complexity tier.
# Calibrated against reference measurements (Ref A/B, ~24 squares, moderate complexity).
LF_FACTORS = {
    #              ridge  hip   valley  rake  flashing  step_flash
    "simple":   (  1.5,  1.5,   0.2,   5.0,   0.6,      0.4  ),
    "moderate": (  1.1,  4.2,   1.6,   4.0,   1.1,      0.9  ),
    "complex":  (  0.8,  5.5,   2.5,   3.0,   1.5,      1.3  ),
}


def pitch_multiplier(degrees: float) -> float:
    for lo, hi, mult in PITCH_MULTIPLIERS:
        if lo <= degrees <= hi:
            return mult
    return 1.54


def estimate_linear_footage(measurements: dict) -> dict:
    squares   = measurements["total_squares"]   # net, before waste
    pitch_deg = measurements["dominant_pitch_deg"]
    tier      = measurements["complexity"]

    # Horizontal footprint → perimeter → eave length
    footprint_sqft = measurements["total_sqft"] / (1 / math.cos(math.radians(pitch_deg))) if pitch_deg < 89 else measurements["total_sqft"]
    eave_lf = math.sqrt(footprint_sqft) * 4

    ridge_f, hip_f, valley_f, rake_f, flash_f, step_f = LF_FACTORS[tier]

    return {
        "ridge_lf":         round(squares * ridge_f),
        "hip_lf":           round(squares * hip_f),
        "valley_lf":        round(squares * valley_f),
        "rake_lf":          round(squares * rake_f),
        "eave_lf":          round(eave_lf),
        "flashing_lf":      round(squares * flash_f),
        "step_flashing_lf": round(squares * step_f),
    }


def build_estimate(measurements: dict) -> dict:
    squares   = measurements["squares_with_waste"]
    pitch_deg = measurements["dominant_pitch_deg"]
    mult      = pitch_multiplier(pitch_deg)
    lf        = estimate_linear_footage(measurements)
    ice_sq    = min(1.5, squares * 0.10)

    line_items = [
        {
            "item":     "Architectural Shingles",
            "qty":      squares,
            "unit":     "squares",
            "rate":     SHINGLE_PER_SQUARE,
            "subtotal": round(squares * SHINGLE_PER_SQUARE, 2),
        },
        {
            "item":     "Labor (pitch-adjusted)",
            "qty":      squares,
            "unit":     "squares",
            "rate":     round(LABOR_PER_SQUARE * mult, 2),
            "subtotal": round(squares * LABOR_PER_SQUARE * mult, 2),
        },
        {
            "item":     "Synthetic Underlayment",
            "qty":      squares,
            "unit":     "squares",
            "rate":     UNDERLAYMENT_PER_SQ,
            "subtotal": round(squares * UNDERLAYMENT_PER_SQ, 2),
        },
        {
            "item":     "Ice & Water Shield (eaves)",
            "qty":      round(ice_sq, 2),
            "unit":     "squares",
            "rate":     ICE_WATER_PER_SQ,
            "subtotal": round(ice_sq * ICE_WATER_PER_SQ, 2),
        },
        {
            "item":     "Ridge Cap",
            "qty":      lf["ridge_lf"],
            "unit":     "lin ft",
            "rate":     RIDGE_CAP_PER_LF,
            "subtotal": round(lf["ridge_lf"] * RIDGE_CAP_PER_LF, 2),
        },
        {
            "item":     "Hip Cap",
            "qty":      lf["hip_lf"],
            "unit":     "lin ft",
            "rate":     HIP_CAP_PER_LF,
            "subtotal": round(lf["hip_lf"] * HIP_CAP_PER_LF, 2),
        },
        {
            "item":     "Valley (metal)",
            "qty":      lf["valley_lf"],
            "unit":     "lin ft",
            "rate":     VALLEY_PER_LF,
            "subtotal": round(lf["valley_lf"] * VALLEY_PER_LF, 2),
        },
        {
            "item":     "Rake Drip Edge",
            "qty":      lf["rake_lf"],
            "unit":     "lin ft",
            "rate":     RAKE_PER_LF,
            "subtotal": round(lf["rake_lf"] * RAKE_PER_LF, 2),
        },
        {
            "item":     "Eave Drip Edge",
            "qty":      lf["eave_lf"],
            "unit":     "lin ft",
            "rate":     EAVE_DRIP_PER_LF,
            "subtotal": round(lf["eave_lf"] * EAVE_DRIP_PER_LF, 2),
        },
        {
            "item":     "Flashing",
            "qty":      lf["flashing_lf"],
            "unit":     "lin ft",
            "rate":     FLASHING_PER_LF,
            "subtotal": round(lf["flashing_lf"] * FLASHING_PER_LF, 2),
        },
        {
            "item":     "Step Flashing",
            "qty":      lf["step_flashing_lf"],
            "unit":     "lin ft",
            "rate":     STEP_FLASHING_PER_LF,
            "subtotal": round(lf["step_flashing_lf"] * STEP_FLASHING_PER_LF, 2),
        },
        {
            "item":     "Tear-off & Disposal",
            "qty":      1,
            "unit":     "flat",
            "rate":     DUMP_FEE,
            "subtotal": DUMP_FEE,
        },
    ]

    subtotal = sum(i["subtotal"] for i in line_items)
    overhead = round(subtotal * OVERHEAD_PROFIT, 2)
    total    = round(subtotal + overhead, 2)

    return {
        "address":          measurements["address"],
        "total_sqft":       measurements["total_sqft"],
        "squares":          squares,
        "dominant_pitch":   f"{measurements['dominant_pitch_rise']} ({pitch_deg}°)",
        "pitch_multiplier": mult,
        "complexity":       measurements["complexity"],
        "linear_footage":   lf,
        "line_items":       line_items,
        "subtotal":         round(subtotal, 2),
        "overhead_profit":  overhead,
        "total":            total,
    }


def print_estimate(est: dict):
    lf = est["linear_footage"]
    print(f"\n{'='*60}")
    print(f"ROOFING ESTIMATE")
    print(f"{'='*60}")
    print(f"Address:    {est['address']}")
    print(f"Roof area:  {est['total_sqft']:,} sq ft  ({est['squares']} squares incl. waste)")
    print(f"Pitch:      {est['dominant_pitch']}  ×{est['pitch_multiplier']} labor multiplier")
    print(f"Complexity: {est['complexity'].title()}")
    print(f"\nLinear Footage:")
    print(f"  Ridge: {lf['ridge_lf']} lf  |  Hip: {lf['hip_lf']} lf  |  Valley: {lf['valley_lf']} lf")
    print(f"  Rake:  {lf['rake_lf']} lf  |  Eave: {lf['eave_lf']} lf")
    print(f"  Flashing: {lf['flashing_lf']} lf  |  Step Flashing: {lf['step_flashing_lf']} lf")
    print(f"\n{'-'*60}")
    print(f"  {'Item':<30} {'Qty':>7} {'Unit':<10} {'Rate':>8} {'Subtotal':>10}")
    print(f"  {'-'*30} {'-'*7} {'-'*10} {'-'*8} {'-'*10}")
    for item in est["line_items"]:
        print(f"  {item['item']:<30} {item['qty']:>7.1f} {item['unit']:<10} ${item['rate']:>7.2f} ${item['subtotal']:>9.2f}")
    print(f"\n  {'Subtotal':<51} ${est['subtotal']:>9.2f}")
    print(f"  {'Overhead & Profit (20%)':<51} ${est['overhead_profit']:>9.2f}")
    print(f"  {'TOTAL':<51} ${est['total']:>9.2f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    address = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "21106 Kenswick Meadows Ct, Humble, TX 77338"
    measurements = measure(address)
    est = build_estimate(measurements)
    print_estimate(est)
