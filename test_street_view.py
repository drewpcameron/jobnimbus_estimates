import os
import requests

API_KEY = os.getenv("GOOGLE_SOLAR_API_KEY")
ADDRESS = "21106 Kenswick Meadows Ct, Humble, TX 77338"

# Step 1 — geocode
geo = requests.get(
    "https://maps.googleapis.com/maps/api/geocode/json",
    params={"address": ADDRESS, "key": API_KEY},
    timeout=10,
)
geo_data = geo.json()
print(f"Geocode status: {geo_data['status']}")
if geo_data["status"] != "OK":
    print(geo_data)
    exit(1)

lat = geo_data["results"][0]["geometry"]["location"]["lat"]
lng = geo_data["results"][0]["geometry"]["location"]["lng"]
print(f"Coords: {lat}, {lng}")

# Step 2 — fetch street view
url = (
    f"https://maps.googleapis.com/maps/api/streetview"
    f"?size=640x480&location={lat},{lng}&fov=90&pitch=0&key={API_KEY}"
)
print(f"Fetching: {url}")

resp = requests.get(url, timeout=10)
print(f"Status code: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('content-type')}")
print(f"Content length: {len(resp.content)} bytes")

if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
    with open("test_street_view_output.jpg", "wb") as f:
        f.write(resp.content)
    print("Saved to test_street_view_output.jpg")
else:
    print("Response body:", resp.text[:500])
