# JobNimbus Hackathon Build Plan
**Deadline: Saturday May 9, 2026 at 1:30 PM**

---

## Status
- [x] Google Solar API working for all 5 test addresses
- [x] pitchDegrees and areaMeters2 confirmed on all segments
- [ ] Measurement engine
- [ ] Estimation logic
- [ ] UI / demo
- [ ] Submission

---

## Step 1 — Validate against benchmark data (1 hour)
Run the 5 *example* properties from `benchmark-measurements.md` through the Solar API and compare
output sqft against the trusted reference measurements.

**Benchmark addresses:**
- 21106 Kenswick Meadows Ct, Humble, TX — reference: 2,443 sqft
- 5914 Copper Lilly Lane, Spring, TX — reference: 4,391 sqft
- 122 NW 13th Ave, Cape Coral, FL — reference: 2,917 sqft
- 14132 Trenton Ave, Orland Park, IL — reference: 2,990 sqft
- 835 S Cobble Creek, Nixa, MO — reference: 3,070 sqft

**Pass criteria:** Solar API sqft within 10–15% of reference for 4/5 addresses.
If it passes, lock in the measurement logic and move on.

---

## Step 2 — Build measurement engine (2 hours)
File: `measurement_engine.py`

Inputs: Solar API response for an address
Outputs:
- Total roof area in sq ft and squares (1 square = 100 sq ft)
- Per-segment breakdown: pitch, area, azimuth (facing direction)
- Dominant pitch (area-weighted average across all segments)
- Complexity tier: Simple (1–4 segs), Moderate (5–8 segs), Complex (9+ segs)
- Waste factor: 10% simple, 12% moderate, 15% complex

---

## Step 3 — Build estimation logic (2 hours)
File: `estimator.py`

Line items to generate:
- Shingles (squares + waste factor)
- Underlayment (squares)
- Ice & water shield (eave length estimate)
- Ridge cap (linear ft estimate from segment count)
- Labor (per square, adjusted for pitch multiplier)
- Dump fee (flat)
- Drip edge (perimeter estimate)

**Pitch multiplier table:**
| Pitch | Multiplier |
|---|---|
| 0–14° (0–3/12) | 1.00 |
| 15–18° (4/12) | 1.06 |
| 19–23° (5/12) | 1.12 |
| 24–27° (6/12) | 1.20 |
| 28–31° (7/12) | 1.30 |
| 32–36° (8–9/12) | 1.41 |
| 37°+ (10/12+) | 1.54 |

---

## Step 4 — Build the UI (3 hours)
File: `app.py` — Streamlit app

Screen 1 — Input:
- Address text field
- "Get Estimate" button

Screen 2 — Output:
- Roof summary card (total sqft, squares, dominant pitch, segment count)
- Line-item estimate table
- Total cost
- "Export to PDF" button (stretch goal)

Run locally with: `streamlit run app.py`

---

## Step 5 — Run all 5 test addresses and record sqft (30 min)
Run the app or script against all 5 hackathon test addresses.
Record the total sqft for each — these go directly into the submission form.

| Address | Sq Ft |
|---|---|
| 3561 E 102nd Ct, Thornton, CO 80229 | |
| 1612 S Canton Ave, Springfield, MO 65802 | |
| 6310 Laguna Bay Court, Houston, TX 77041 | |
| 3820 E Rosebrier St, Springfield, MO 65809 | |
| 1261 20th Street, Newport News, VA 23607 | |

---

## Step 6 — Polish and push to GitHub (1 hour)
- Write README.md (what it does, how to run it, tech stack)
- Make repo public
- Add output screenshots or JSON for each test property

---

## Step 7 — Submit (15 min)
Google Form requires:
- Team info
- Approach summary (≤200 words): Google Solar API → geopy geocoding → pitch-adjusted estimation engine → Streamlit UI
- Public GitHub repo link
- Square footage for all 5 test addresses
- Optional demo video
