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

## Judging Criteria

### 1. Accuracy
Measurements are sourced directly from the **Google Solar API** — the same satellite and aerial imagery pipeline used by Google's Project Sunroof, which has processed over 320 million rooftops globally.

Validated against the provided EagleView/Geospan benchmark data across all 5 reference properties:

| Address | Reference (sqft) | Our Output (sqft) | Error |
|---|---|---|---|
| 21106 Kenswick Meadows Ct, Humble TX | 2,443 | 2,404 | 1.6% |
| 5914 Copper Lilly Lane, Spring TX | 4,391 | 4,468 | 1.8% |
| 122 NW 13th Ave, Cape Coral FL | 2,917 | 2,961 | 1.5% |
| 14132 Trenton Ave, Orland Park IL | 2,990 | 3,044 | 1.8% |
| 835 S Cobble Creek, Nixa MO | 3,070 | 3,126 | 1.9% |

**Average error: 1.7%** — well within the EagleView/Geospan tolerance range.

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
| 3561 E 102nd Ct, Thornton, CO 80229 | |
| 1612 S Canton Ave, Springfield, MO 65802 | |
| 6310 Laguna Bay Court, Houston, TX 77041 | |
| 3820 E Rosebrier St, Springfield, MO 65809 | |
| 1261 20th Street, Newport News, VA 23607 | |

---

## Cost Per Estimate

Each full estimate — geocoding, Solar API measurement, Street View confirmation, and Places Autocomplete — costs **less than $0.01** in total API calls. At scale, this is a negligible cost per job for any roofing contractor.

---

## Why Google Solar API

Most approaches to aerial roof measurement use a vision model to interpret satellite images — which introduces hallucination risk and produces measurements that can't be audited or reproduced. The Google Solar API provides structured geometric data extracted from aerial imagery and LiDAR at the segment level: each roof plane's area, pitch, and orientation as discrete values. The result is a measurement pipeline that is deterministic, fast (~700ms), and accurate to within 2% of trusted industry reference data.
