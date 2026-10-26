"""Smoke-test the new tool against Amazon Location Service WITHOUT calling Bedrock.

    python -m demo.check_location

Run this first: if it prints three verdicts, your IAM + region setup for the tool is correct.
"""
import json

from agent.geo_velocity import LocationGeocoder, assess

CASES = [
    ("Dubai Mall, Dubai, United Arab Emirates", "2026-10-24T04:10:00Z",
     "Oxford Street, London, United Kingdom", "2026-10-24T05:25:00Z"),
    ("Dubai Mall, Dubai, United Arab Emirates", "2026-10-24T04:10:00Z",
     "Corniche Road, Abu Dhabi, United Arab Emirates", "2026-10-24T07:05:00Z"),
    ("Cairo International Airport, Cairo, Egypt", "2026-10-24T06:00:00Z",
     "Gold Souk, Deira, Dubai, United Arab Emirates", "2026-10-24T12:30:00Z"),
]

if __name__ == "__main__":
    geo = LocationGeocoder()
    for a, ta, b, tb in CASES:
        v = assess(geo.geocode(a), ta, geo.geocode(b), tb)
        print(json.dumps({"from": a, "to": b, "verdict": v.verdict, "risk": v.risk,
                          "distance_km": v.distance_km, "elapsed_h": v.elapsed_hours,
                          "speed_kmh": v.implied_speed_kmh,
                          "tz": [v.origin["time_zone"], v.destination["time_zone"]]}, indent=2))
