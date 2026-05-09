# JobNimbus Hackathon Build Plan
**Deadline: Saturday May 9, 2026 at 1:30 PM**

---

## Status
- [x] Google Solar API working for all 5 test addresses
- [x] pitchDegrees and areaMeters2 confirmed on all segments
- [x] Measurement engine
- [x] Estimation logic
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

### Stage machine
Use `st.session_state` to track 4 stages: `"input"` → `"confirm"` → `"analyzing"` → `"results"`.
Each stage renders a different screen; Streamlit re-runs on every interaction so all logic is driven by state.

### Stage 1 — Address Entry
- Address text field + "Get Estimate" button
- On submit: geocode address (already works), advance to `"confirm"`

### Stage 2 — Street View Confirmation
- Enable **Google Street View Static API** in Google Cloud Console (same key)
- Fetch Street View JPEG using lat/lng from geocoder
- Display image with "Is this your property?" prompt + Yes / No buttons
- Yes → kick off Solar API call immediately, store result in `session_state`, advance to `"analyzing"`

### Stage 3 — Animation (via `st.components.v1.html()`)
Three CSS animations chained in sequence inside a single HTML block:
1. **Crossfade** — Street View JPEG fades to Maps Static satellite JPEG (enable **Google Maps Static API**, same key)
2. **Perspective flatten** — satellite image animates from `rotateX(45deg)` to `rotateX(0)` using CSS `transform: perspective()`
3. **Scan line** — semi-transparent `div` sweeps top-to-bottom over the flattened roof image via `@keyframes`

Total animation runtime ~3–4 seconds. Solar API call (~0.7s) is already done by the time animation ends — result is pulled from `session_state` and displayed immediately after.

### Stage 4 — Results
- Fade/slide in existing estimate output (roof summary cards + line-item table + total)
- "Start Over" button resets session state to `"input"`

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

## Nice to Haves
- **Address autocomplete** — Enable Google Places Autocomplete API (same key), implement via `st.components.v1.html()` with the Places JS SDK. Suggestions appear as user types; selected address is passed back to `st.session_state` via postMessage. ~20–30 min.
- **Full confirmation animation (zoom + flatten + scan)** — After house confirmation, street view zooms in (`transform: scale()`), crossfades to Google Maps Static satellite image, satellite tilts from `perspective rotateX(45deg)` down to flat, then a scan line sweeps top-to-bottom. All CSS keyframes in a `st.components.v1.html()` block with both images base64-encoded. Requires a `time.sleep(3)` after the Solar API call so the animation plays fully before results render. ~2–3 hours.
- **Satellite segment overlay with hover costs** — Overlay roof segment outlines on the satellite image with per-segment cost breakdown on hover. Requires Solar API `dataLayers:get` endpoint (GeoTIFF rasters) to extract polygon boundaries, `rasterio`/`shapely` for coordinate projection, and a custom `st.components.v1.html()` canvas component for hover interaction. Strong demo/wow feature but limited daily contractor utility. ~6–8 hours, high implementation risk.

---

## Step 7 — Submit (15 min)
Google Form requires:
- Team info
- Approach summary (≤200 words): Google Solar API → geopy geocoding → pitch-adjusted estimation engine → Streamlit UI
- Public GitHub repo link
- Square footage for all 5 test addresses
- Optional demo video
