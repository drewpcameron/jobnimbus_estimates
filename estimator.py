"""
Converts roof measurements into a line-item roofing estimate.
"""

import math
from measurement_engine import measure


# ── Pricing constants ─────────────────────────────────────────────────────────

SHINGLE_PER_SQUARE    = 135.00   # architectural shingles
LABOR_PER_SQUARE      = 175.00   # base labor
UNDERLAYMENT_PER_SQ   = 25.00
ICE_WATER_PER_SQ      = 75.00    # applied to eave rows (~1.5 squares avg house)
RIDGE_CAP_PER_LF      = 5.00
DRIP_EDGE_PER_LF      = 2.00
DUMP_FEE              = 350.00
OVERHEAD_PROFIT       = 0.20

# Pitch multiplier applied to labor (steeper = harder/slower)
PITCH_MULTIPLIERS = [
    (0,  14,  1.00),
    (15, 18,  1.06),
    (19, 23,  1.12),
    (24, 27,  1.20),
    (28, 31,  1.30),
    (32, 36,  1.41),
    (37, 90,  1.54),
]


def pitch_multiplier(degrees: float) -> float:
    for lo, hi, mult in PITCH_MULTIPLIERS:
        if lo <= degrees <= hi:
            return mult
    return 1.54


def estimate_ridge_lf(measurements: dict) -> float:
    """Rough ridge linear footage from total squares."""
    return measurements["total_squares"] * 3.5


def estimate_perimeter_lf(measurements: dict) -> float:
    """Rough perimeter from total sqft (assumes roughly square footprint)."""
    footprint_sqft = measurements["total_sqft"] / (1 / math.cos(math.radians(measurements["dominant_pitch_deg"])))
    side = math.sqrt(footprint_sqft)
    return side * 4


def build_estimate(measurements: dict) -> dict:
    squares    = measurements["squares_with_waste"]
    pitch_deg  = measurements["dominant_pitch_deg"]
    mult       = pitch_multiplier(pitch_deg)
    ridge_lf   = estimate_ridge_lf(measurements)
    perim_lf   = estimate_perimeter_lf(measurements)
    ice_sq     = min(1.5, squares * 0.10)  # ice & water on eaves only

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
            "qty":      round(ridge_lf),
            "unit":     "lin ft",
            "rate":     RIDGE_CAP_PER_LF,
            "subtotal": round(ridge_lf * RIDGE_CAP_PER_LF, 2),
        },
        {
            "item":     "Drip Edge",
            "qty":      round(perim_lf),
            "unit":     "lin ft",
            "rate":     DRIP_EDGE_PER_LF,
            "subtotal": round(perim_lf * DRIP_EDGE_PER_LF, 2),
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
        "line_items":       line_items,
        "subtotal":         round(subtotal, 2),
        "overhead_profit":  overhead,
        "total":            total,
    }


def print_estimate(est: dict):
    print(f"\n{'='*60}")
    print(f"ROOFING ESTIMATE")
    print(f"{'='*60}")
    print(f"Address:   {est['address']}")
    print(f"Roof area: {est['total_sqft']:,} sq ft  ({est['squares']} squares incl. waste)")
    print(f"Pitch:     {est['dominant_pitch']}  ×{est['pitch_multiplier']} labor multiplier")
    print(f"Complexity: {est['complexity'].title()}")
    print(f"\n{'-'*60}")
    print(f"  {'Item':<30} {'Qty':>7} {'Unit':<8} {'Rate':>8} {'Subtotal':>10}")
    print(f"  {'-'*30} {'-'*7} {'-'*8} {'-'*8} {'-'*10}")
    for item in est["line_items"]:
        print(f"  {item['item']:<30} {item['qty']:>7.1f} {item['unit']:<8} ${item['rate']:>7.2f} ${item['subtotal']:>9.2f}")
    print(f"\n  {'Subtotal':<49} ${est['subtotal']:>9.2f}")
    print(f"  {'Overhead & Profit (20%)':<49} ${est['overhead_profit']:>9.2f}")
    print(f"  {'TOTAL':<49} ${est['total']:>9.2f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    address = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "21106 Kenswick Meadows Ct, Humble, TX 77338"
    measurements = measure(address)
    est = build_estimate(measurements)
    print_estimate(est)
