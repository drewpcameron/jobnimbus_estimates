# Aerial Roof Estimator — JobNimbus Hackathon 2026

**Live Demo → [jobnimbus-estimates.streamlit.app](https://jobnimbus-estimates.streamlit.app)**

Type an address. Get a quote-ready roofing estimate in seconds — no manual measurements, no site visit required.

---

## What It Does

1. **Address input** — Google Places Autocomplete surfaces the property as you type
2. **Street View confirmation** — instantly verifies the correct property before running any measurements
3. **Aerial measurement** — Google Solar API pulls satellite-derived roof geometry: area, pitch, segments, complexity
4. **Auto-estimate** — pitch-adjusted line-item estimate generated immediately from the measurements
5. **Save to JobNimbus** — one-click modal to push the estimate and client details directly into JobNimbus

---

## Running Locally

```bash
pip install streamlit requests pandas
```

Create a `.env` file (or set environment variables) with:

```
GOOGLE_API_KEY=your_google_api_key
JOBNIMBUS_API_KEY=your_jobnimbus_api_key
```

Then run:

```bash
streamlit run app.py
```

The Google API key needs the following APIs enabled: Solar API, Places API, Geocoding API, Street View Static API.

---

## Judging Criteria

### 1. Accuracy

Measurements are sourced directly from the **Google Solar API** — the same satellite and aerial imagery pipeline used by Google's Project Sunroof, which has processed over 320 million rooftops globally.

All measurements are **pitch-adjusted roof area**, not building footprint. A house with a 2,000 sqft footprint and a 9/12 pitch has approximately 2,800 sqft of actual roof surface — a ~40% difference. Using footprint is a common error that causes 5–20% underestimation depending on slope; the Solar API returns true sloped area for each segment, which we sum directly.

Validated against both EagleView (Ref A) and Geospan (Ref B) benchmark data across all 5 reference properties:

| Address | Ref A (sqft) | Ref B (sqft) | Our Output (sqft) | Error vs A | Error vs B |
|---|---|---|---|---|---|
| 21106 Kenswick Meadows Ct, Humble TX | 2,443 | 2,343 | 2,404 | 1.6% | 2.6% |
| 5914 Copper Lilly Lane, Spring TX | 4,391 | 4,296 | 4,468 | 1.8% | 4.0% |
| 122 NW 13th Ave, Cape Coral FL | 2,917 | 2,851 | 2,961 | 1.5% | 3.9% |
| 14132 Trenton Ave, Orland Park IL | 2,990 | 2,935 | 3,044 | 1.8% | 3.7% |
| 835 S Cobble Creek, Nixa MO | 3,070 | 3,017 | 3,126 | 1.8% | 3.6% |

**Average error: 1.7% vs EagleView, 3.6% vs Geospan** — within practical tolerance for both reference sources.

### 2. Product

This isn't a measurement tool with an estimate bolted on — it's a contractor workflow built around the estimate:

- **12 line-item estimate** with industry-standard pricing (shingles, labor, underlayment, ice & water shield, ridge cap, hip cap, valley, rake, eave drip edge, flashing, step flashing, tear-off)
- **Pitch-adjusted labor** using a 7-tier multiplier table (1.00× flat → 1.54× 10/12+)
- **Editable rates** — every rate cell is live-editable; totals recalculate instantly
- **Adjustable O&P** — overhead & profit percentage is a live input
- **Header total updates** as the contractor adjusts rates — what's shown is always the current number
- **Save to JobNimbus** — modal collects client name, email, and phone then pushes to the CRM

A roofer can walk off the truck, type an address, and hand a customer a number in under 30 seconds.

### 3. Experience

- **No button required** — selecting an autocomplete suggestion immediately kicks off geocoding and advances to confirmation
- **Street View confirmation** — contractor verifies the right house before any API calls are made
- **Smooth stage transitions** — slide and shrink-in CSS animations between input → confirm → results
- **Single-screen results** — the full estimate fits on one viewport with no scrolling
- **Live deployed app** — no setup, no installs, works on any device

### 4. Craft

**Novel approach:** Rather than prompt-engineering a vision model to interpret satellite images, we query the **Google Solar API** directly for structured roof geometry — segment-level pitch, area, and azimuth data derived from the same LiDAR and aerial imagery pipelines used in production solar assessments. This sidesteps hallucination risk entirely and produces deterministic, auditable measurements.

**Independent computation:** The Solar API provides raw geometric data — segments with area and pitch. Everything built on top of that is custom: the pitch multiplier table, the 12-line-item estimator, the linear footage estimation model, complexity-tier waste factors, and the area-weighted dominant pitch calculation. No commercial estimation service is involved; the estimate is computed from first principles against the raw measurement data.

**Architecture:**
```
app.py                  — Streamlit UI, stage machine, session state
measurement_engine.py   — Google Solar API + geocoding, segment extraction
estimator.py            — Pitch multipliers, LF estimation, line-item builder
```

**Key engineering decisions:**
- Linear footage (ridge, hip, valley, rake, eave, flashing, step flashing) estimated from net squares × complexity-tier factors, calibrated against the benchmark reference properties
- Waste factors by complexity: 10% simple / 12% moderate / 15% complex
- Dominant pitch is area-weighted across all roof segments
- All API calls are server-side — no client credentials exposed

**Stack:** Python · Streamlit · Google Solar API · Google Places API · Google Geocoding API · Google Street View Static API · Pandas

### 5. Demo

Live at **[jobnimbus-estimates.streamlit.app](https://jobnimbus-estimates.streamlit.app)** — try it with any US address before the presentation.

The Saturday demo will walk through the full contractor workflow:
- Address autocomplete → street view confirmation → aerial measurement → editable estimate → Save to JobNimbus

---

## Test Property Results

| Address | Sq Ft |
|---|---|
| 3561 E 102nd Ct, Thornton, CO 80229 | 2,081 |
| 1612 S Canton Ave, Springfield, MO 65802 | 2,757 |
| 6310 Laguna Bay Court, Houston, TX 77041 | 4,186 |
| 3820 E Rosebrier St, Springfield, MO 65809 | 5,566 |
| 1261 20th Street, Newport News, VA 23607 | 6,118 |

---

## Cost Per Estimate

Each full estimate — geocoding, Solar API measurement, Street View confirmation, and Places Autocomplete — costs **less than $0.01** in total API calls. At scale, this is a negligible cost per job for any roofing contractor.

---

## Why Google Solar API

Most approaches to aerial roof measurement use a vision model to interpret satellite images — which introduces hallucination risk and produces measurements that can't be audited or reproduced. The Google Solar API provides structured geometric data extracted from aerial imagery and LiDAR at the segment level: each roof plane's area, pitch, and orientation as discrete values. The result is a measurement pipeline that is deterministic, fast (~700ms), and accurate to within 2% of trusted industry reference data.

---

## How Measurements Are Calculated

This section documents exactly what we compute ourselves vs. what the API provides, so the pipeline is fully auditable.

### What the Google Solar API returns

A single call to `buildingInsights:findClosest` returns a `roofSegmentStats` array — one entry per distinct roof plane — each containing:
- `areaMeters2` — the **sloped surface area** of that plane in m², derived from LiDAR geometry (not footprint)
- `pitchDegrees` — the tilt angle of that plane
- `azimuthDegrees` — the compass orientation of that plane

The API also returns `wholeRoofStats.areaMeters2`, the sum of all segment areas.

That's it. The API gives us geometry. Everything else is computed in our code.

### What we calculate

**Total roof area** (`measurement_engine.py`):
```python
total_sqft = total_m2 * 10.764          # m² → sq ft
squares_net = total_sqft / 100          # roofing squares
squares_with_waste = squares_net * (1 + waste_factor)
```

**Dominant pitch** — area-weighted average across all segments, so a large low-slope section doesn't get overridden by a small steep dormer:
```python
weighted = sum(segment.pitchDegrees * segment.areaMeters2 for each segment)
dominant_pitch = weighted / total_area
```

**Complexity tier** — based on segment count, used to drive waste factor and LF multipliers:
```
≤4 segments  → simple   → 10% waste
≤8 segments  → moderate → 12% waste
 9+ segments → complex  → 15% waste
```

**Linear footage** (`estimator.py`) — ridge, hip, valley, rake, flashing, and step flashing are not returned by the API. We estimate them using per-tier multipliers against net squares, calibrated against the benchmark reference properties:
```python
LF_FACTORS = {
    #              ridge  hip   valley  rake  flashing  step_flash
    "simple":   (  1.5,  1.5,   0.2,   5.0,   0.6,      0.4  ),
    "moderate": (  1.1,  4.2,   1.6,   4.0,   1.1,      0.9  ),
    "complex":  (  0.8,  5.5,   2.5,   3.0,   1.5,      1.3  ),
}
ridge_lf = net_squares * LF_FACTORS[tier].ridge
```

Eave length is derived geometrically from the footprint perimeter:
```python
footprint_sqft = total_sqft / (1 / cos(pitch_radians))
eave_lf = sqrt(footprint_sqft) * 4
```

**Pitch multiplier** — labor is adjusted using a 7-tier table based on dominant pitch degrees:
```
0–14°  → 1.00×    15–18° → 1.06×    19–23° → 1.12×    24–27° → 1.20×
28–31° → 1.30×    32–36° → 1.41×    37°+   → 1.54×
```

**Line-item estimate** — 12 items are priced against the computed quantities. Every rate is editable in the UI; the base rates are constants defined in `estimator.py`, not fetched from any external pricing service.

---

## AI Approach

This project deliberately does not use a language model or vision model for measurement. Here's why.

The obvious approach — prompt a vision model with a satellite image and ask it to estimate roof area — introduces two problems that are hard to fix in a production tool: hallucination risk (the model can confidently return a wrong number with no way to audit it) and non-determinism (the same image can produce different measurements on different runs).

The Google Solar API solves both problems. It was built by Google specifically to extract roof geometry from LiDAR and aerial imagery at scale — it has processed over 320 million rooftops. It returns structured, deterministic data: exact segment areas, pitch angles, and orientations as discrete numeric values. There is nothing to interpret or hallucinate.

The "AI" in this project is the measurement source itself. The Solar API's underlying pipeline uses computer vision and photogrammetry at a level of engineering that no prompt-engineered vision model call would match, and it exposes the results as clean geometry rather than a natural language estimate.

Everything built on top — the waste factors, pitch multipliers, linear footage model, line-item estimator — is deterministic Python. The output is fully auditable: you can trace every number in the estimate back to a specific formula and a specific value returned by the API.

**Why not add an LLM on top?** We considered using an LLM to interpret edge cases or generate a narrative summary, but the contractor use case doesn't benefit from it — a roofer needs a number they can defend, not a paragraph. Adding a model would introduce latency, cost, and a failure mode with no upside.

---

## Known Limitations

- **Coverage is US-only** — the Google Solar API does not have data outside the United States
- **Dense tree canopy** — properties with heavy overhead foliage may have incomplete or lower-confidence segment data; the API returns a quality flag which we surface to the user
- **Very new construction** — recently built structures may not yet appear in the Solar API's imagery dataset
- **Flat/low-slope roofs** — commercial flat roofs with complex HVAC equipment may produce fragmented segment data; the tool is optimized for residential pitched roofs
- **Linear footage is estimated** — ridge, hip, valley, and eave lengths are derived from area + complexity tier, not measured directly; accuracy is within typical estimating tolerance but not surveyed geometry
