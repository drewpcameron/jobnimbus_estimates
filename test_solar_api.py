"""
Google Solar API validation tests for Salt Lake City coverage.

Run:
    pip install requests python-dotenv
    cp .env.example .env   # then add your key
    python test_solar_api.py

Pass criteria:
    - pitchDegrees + areaMeters2 present for 3+ of 4 addresses  -> BUILD
    - errors / missing fields for most addresses                 -> STOP
"""

import os
import time
import requests

API_KEY = os.getenv("GOOGLE_SOLAR_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
SOLAR_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"

# Benchmark properties with known reference sqft for accuracy validation
ADDRESSES = [
    {"address": "21106 Kenswick Meadows Ct, Humble, TX 77338",  "reference_sqft": 2443},
    {"address": "5914 Copper Lilly Lane, Spring, TX 75379",      "reference_sqft": 4391},
    {"address": "122 NW 13th Ave, Cape Coral, FL 33993",         "reference_sqft": 2917},
    {"address": "14132 Trenton Ave, Orland Park, IL 60462",      "reference_sqft": 2990},
    {"address": "835 S Cobble Creek, Nixa, MO 65714",            "reference_sqft": 3070},
]

REQUIRED_FIELDS = [
    "solarPotential.roofSegmentStats",
    "solarPotential.wholeRoofStats.areaMeters2",
]


# ── helpers ──────────────────────────────────────────────────────────────────

def geocode(address: str) -> tuple[float, float] | None:
    try:
        r = requests.get(GEOCODE_URL, params={"address": address, "key": API_KEY}, timeout=10)
        data = r.json()
        status = data.get("status")
        if status != "OK":
            print(f"  Geocode failed — status: {status}  {data.get('error_message', '')}")
            return None
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    except Exception as e:
        print(f"  Geocode exception: {e}")
        return None


def get_solar(lat: float, lng: float) -> tuple[dict, float]:
    params = {
        "location.latitude": lat,
        "location.longitude": lng,
        "requiredQuality": "LOW",  # maximise coverage; HIGH can silently exclude addresses
        "key": API_KEY,
    }
    t0 = time.perf_counter()
    r = requests.get(SOLAR_URL, params=params, timeout=30)
    elapsed = time.perf_counter() - t0
    return r, elapsed


def get_nested(d: dict, dotpath: str):
    """Walk a.b.c paths into a dict."""
    for key in dotpath.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def check_segment(seg: dict, idx: int) -> list[str]:
    issues = []
    if seg.get("pitchDegrees") is None:
        issues.append(f"  segment[{idx}] missing pitchDegrees")
    if get_nested(seg, "stats.areaMeters2") is None:
        issues.append(f"  segment[{idx}] missing stats.areaMeters2")
    return issues


# ── main test ────────────────────────────────────────────────────────────────

def run_tests():
    if not API_KEY:
        print("ERROR: GOOGLE_SOLAR_API_KEY not set")
        return

    print("=" * 64)
    print("Google Solar API — Benchmark Accuracy Validation")
    print("=" * 64)

    results_summary = []

    for entry in ADDRESSES:
        address = entry["address"]
        reference = entry["reference_sqft"]
        print(f"\nAddress: {address}")
        print(f"  Reference: {reference:,} sq ft")

        coords = geocode(address)
        if not coords:
            print("  FAIL  — geocoding returned no results")
            results_summary.append((address, reference, None, "geocode failed"))
            continue
        lat, lng = coords
        print(f"  Coords: {lat:.5f}, {lng:.5f}")

        try:
            response, elapsed = get_solar(lat, lng)
        except requests.exceptions.Timeout:
            print("  FAIL  — request timed out (>30s)")
            results_summary.append((address, reference, None, "timeout"))
            continue

        print(f"  HTTP {response.status_code}  |  {elapsed:.2f}s")

        if response.status_code != 200:
            err = response.json().get("error", {})
            print(f"  FAIL  — {err.get('status', '?')}: {err.get('message', response.text[:120])}")
            results_summary.append((address, reference, None, f"HTTP {response.status_code}"))
            continue

        data = response.json()

        missing_top = [f for f in REQUIRED_FIELDS if get_nested(data, f) is None]
        if missing_top:
            print(f"  FAIL  — missing fields: {missing_top}")
            results_summary.append((address, reference, None, f"missing fields"))
            continue

        segments  = data["solarPotential"]["roofSegmentStats"]
        total_m2  = data["solarPotential"]["wholeRoofStats"]["areaMeters2"]
        total_sqft = total_m2 * 10.764

        pitch_values = [s.get("pitchDegrees") for s in segments if s.get("pitchDegrees") is not None]
        n_segs = len(segments)
        diff = total_sqft - reference
        pct  = (diff / reference) * 100

        print(f"  Segments:   {n_segs}")
        print(f"  Pitch range: {min(pitch_values):.1f}° – {max(pitch_values):.1f}°" if pitch_values else "  Pitch: MISSING")
        print(f"  Solar sqft:  {total_sqft:,.0f}")
        print(f"  Reference:   {reference:,}")
        print(f"  Difference:  {diff:+,.0f} sq ft  ({pct:+.1f}%)")

        results_summary.append((address, reference, total_sqft, pct))

    # ── Accuracy summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("ACCURACY SUMMARY\n")
    print(f"  {'Address':<45} {'Ref':>6} {'Solar':>6} {'Diff':>8}")
    print(f"  {'-'*45} {'-'*6} {'-'*6} {'-'*8}")

    errors = []
    for address, ref, solar, note in results_summary:
        if solar is None:
            print(f"  {address:<45} {ref:>6,}   FAIL   {note}")
        else:
            print(f"  {address:<45} {ref:>6,} {solar:>6,.0f}  {note:>+.1f}%")
            errors.append(abs(note))

    if errors:
        avg_err = sum(errors) / len(errors)
        print(f"\n  Average error: {avg_err:.1f}%")
        if avg_err <= 10:
            print("  VERDICT: Excellent accuracy — submit as-is.")
        elif avg_err <= 20:
            print("  VERDICT: Good accuracy — within acceptable range for judging.")
        else:
            print("  VERDICT: High error — consider applying a correction factor.")
    print("=" * 64)


if __name__ == "__main__":
    run_tests()
