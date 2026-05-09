"""
Converts a property address into roof measurements using the Google Solar API.
"""

import os
import math
import requests

API_KEY = os.getenv("GOOGLE_SOLAR_API_KEY")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
SOLAR_URL   = "https://solar.googleapis.com/v1/buildingInsights:findClosest"


def geocode(address: str) -> tuple[float, float]:
    r = requests.get(GEOCODE_URL, params={"address": address, "key": API_KEY}, timeout=10)
    data = r.json()
    if data.get("status") != "OK":
        raise ValueError(f"Geocoding failed for '{address}': {data.get('status')} {data.get('error_message', '')}")
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def get_solar_data(lat: float, lng: float) -> dict:
    params = {
        "location.latitude":  lat,
        "location.longitude": lng,
        "requiredQuality":    "LOW",
        "key":                API_KEY,
    }
    r = requests.get(SOLAR_URL, params=params, timeout=30)
    if r.status_code != 200:
        err = r.json().get("error", {})
        raise ValueError(f"Solar API error: {err.get('status')} — {err.get('message')}")
    return r.json()


def pitch_to_rise(degrees: float) -> str:
    """Convert degrees to nearest x/12 pitch string."""
    rise = round(math.tan(math.radians(degrees)) * 12)
    return f"{rise}/12"


def dominant_pitch(segments: list) -> float:
    """Area-weighted average pitch across all segments."""
    total_area  = sum(s.get("stats", {}).get("areaMeters2", 0) for s in segments)
    if total_area == 0:
        return 0
    weighted = sum(
        s.get("pitchDegrees", 0) * s.get("stats", {}).get("areaMeters2", 0)
        for s in segments
    )
    return weighted / total_area


def complexity_tier(n_segments: int) -> str:
    if n_segments <= 4:
        return "simple"
    if n_segments <= 8:
        return "moderate"
    return "complex"


def waste_factor(tier: str) -> float:
    return {"simple": 0.10, "moderate": 0.12, "complex": 0.15}[tier]


def measure_from_coords(lat: float, lng: float, address: str) -> dict:
    """Run Solar API + measurement pipeline when lat/lng are already known."""
    data     = get_solar_data(lat, lng)
    solar    = data["solarPotential"]
    segments = solar["roofSegmentStats"]
    total_m2 = solar["wholeRoofStats"]["areaMeters2"]

    total_sqft   = total_m2 * 10.764
    dom_pitch    = dominant_pitch(segments)
    tier         = complexity_tier(len(segments))
    waste        = waste_factor(tier)
    squares_net  = total_sqft / 100
    squares_with_waste = squares_net * (1 + waste)

    seg_details = [
        {
            "pitch_degrees": s.get("pitchDegrees", 0),
            "pitch_rise":    pitch_to_rise(s.get("pitchDegrees", 0)),
            "area_sqft":     (s.get("stats", {}).get("areaMeters2", 0)) * 10.764,
            "azimuth":       s.get("azimuthDegrees", 0),
        }
        for s in segments
    ]

    return {
        "address":             address,
        "lat":                 lat,
        "lng":                 lng,
        "total_sqft":          round(total_sqft),
        "total_squares":       round(squares_net, 2),
        "squares_with_waste":  round(squares_with_waste, 2),
        "dominant_pitch_deg":  round(dom_pitch, 1),
        "dominant_pitch_rise": pitch_to_rise(dom_pitch),
        "segment_count":       len(segments),
        "complexity":          tier,
        "waste_factor":        waste,
        "segments":            seg_details,
    }


def measure(address: str) -> dict:
    """
    Main entry point. Returns a measurement dict for the given address.
    Raises ValueError if geocoding or Solar API fails.
    """
    lat, lng = geocode(address)
    data     = get_solar_data(lat, lng)

    solar    = data["solarPotential"]
    segments = solar["roofSegmentStats"]
    total_m2 = solar["wholeRoofStats"]["areaMeters2"]

    total_sqft   = total_m2 * 10.764
    dom_pitch    = dominant_pitch(segments)
    tier         = complexity_tier(len(segments))
    waste        = waste_factor(tier)
    squares_net  = total_sqft / 100
    squares_with_waste = squares_net * (1 + waste)

    seg_details = [
        {
            "pitch_degrees": s.get("pitchDegrees", 0),
            "pitch_rise":    pitch_to_rise(s.get("pitchDegrees", 0)),
            "area_sqft":     (s.get("stats", {}).get("areaMeters2", 0)) * 10.764,
            "azimuth":       s.get("azimuthDegrees", 0),
        }
        for s in segments
    ]

    return {
        "address":             address,
        "lat":                 lat,
        "lng":                 lng,
        "total_sqft":          round(total_sqft),
        "total_squares":       round(squares_net, 2),
        "squares_with_waste":  round(squares_with_waste, 2),
        "dominant_pitch_deg":  round(dom_pitch, 1),
        "dominant_pitch_rise": pitch_to_rise(dom_pitch),
        "segment_count":       len(segments),
        "complexity":          tier,
        "waste_factor":        waste,
        "segments":            seg_details,
    }


if __name__ == "__main__":
    import sys
    import json
    address = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "21106 Kenswick Meadows Ct, Humble, TX 77338"
    result = measure(address)
    print(json.dumps(result, indent=2))
