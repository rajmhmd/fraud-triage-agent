"""Geo-velocity ("impossible travel") engine.

Pure, deterministic logic, kept separate from the LLM and from AWS so it can
be unit-tested and audited. The geocoder is injected: in production it is
Amazon Location Service (LocationGeocoder); in tests it is a dict-backed fake.

Why deterministic: the model decides WHEN to check travel and HOW to explain
it, but the verdict itself must be reproducible for a fraud analyst or an
auditor. An LLM estimating "Dubai to London is ~5,000 km" is not evidence.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional, Protocol

from . import config

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class GeoPoint:
    query: str
    label: str
    lon: float
    lat: float
    country_code: Optional[str] = None
    time_zone: Optional[str] = None


class Geocoder(Protocol):
    def geocode(self, query: str) -> GeoPoint: ...


class GeocodingError(Exception):
    pass


def haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    """Great-circle distance in km (WGS 84 mean radius)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def _parse_utc(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone/offset: {ts}")
    return dt


@dataclass(frozen=True)
class TravelVerdict:
    verdict: str                 # FEASIBLE_SAME_AREA | FEASIBLE_BY_GROUND | FEASIBLE_BY_AIR | IMPOSSIBLE
    risk: str                    # LOW | MEDIUM | HIGH
    distance_km: float
    elapsed_hours: float
    implied_speed_kmh: Optional[float]
    min_air_hours_needed: float
    origin: dict
    destination: dict
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def assess(origin: GeoPoint, origin_ts: str, dest: GeoPoint, dest_ts: str) -> TravelVerdict:
    """Decide whether one person could physically be at both points in time."""
    t1, t2 = _parse_utc(origin_ts), _parse_utc(dest_ts)
    if t2 < t1:  # order-independent: always measure forward in time
        origin, dest, t1, t2 = dest, origin, t2, t1
    elapsed_h = (t2 - t1).total_seconds() / 3600
    dist = haversine_km(origin, dest)
    speed = dist / elapsed_h if elapsed_h > 0 else None
    min_air_h = config.AIR_OVERHEAD_HOURS + dist / config.AIR_CRUISE_KMH

    if dist <= config.SAME_METRO_KM:
        verdict, risk = "FEASIBLE_SAME_AREA", "LOW"
        why = f"Both locations are within {config.SAME_METRO_KM:.0f} km of each other."
    elif elapsed_h * config.MAX_GROUND_KMH >= dist:
        verdict, risk = "FEASIBLE_BY_GROUND", "LOW"
        why = f"{dist:.0f} km in {elapsed_h:.2f} h is achievable by road (<= {config.MAX_GROUND_KMH:.0f} km/h)."
    elif elapsed_h >= min_air_h:
        verdict, risk = "FEASIBLE_BY_AIR", "MEDIUM"
        why = (f"{dist:.0f} km needs a flight (>= {min_air_h:.1f} h incl. airport overhead); "
               f"{elapsed_h:.1f} h elapsed, so possible only if the cardholder flew.")
    else:
        verdict, risk = "IMPOSSIBLE", "HIGH"
        why = (f"{dist:.0f} km in {elapsed_h:.2f} h implies ~{(speed or float('inf')):.0f} km/h; "
               f"even a direct flight needs >= {min_air_h:.1f} h.")

    return TravelVerdict(
        verdict=verdict,
        risk=risk,
        distance_km=round(dist, 1),
        elapsed_hours=round(elapsed_h, 2),
        implied_speed_kmh=round(speed, 1) if speed is not None else None,
        min_air_hours_needed=round(min_air_h, 2),
        origin={**asdict(origin), "timestamp_utc": t1.isoformat()},
        destination={**asdict(dest), "timestamp_utc": t2.isoformat()},
        explanation=why,
    )


class LocationGeocoder:
    """Amazon Location Service (Places API v2: geo-places Geocode) with an in-memory cache.

    Uses SigV4 (IAM) auth via the default boto3 credential chain, so no API key
    is needed. IntendedUse defaults to SingleUse: results are not persisted.
    """

    def __init__(self, region: str = config.LOCATION_REGION, client=None):
        if client is None:
            import boto3  # imported lazily so unit tests need no AWS SDK
            client = boto3.client("geo-places", region_name=region)
        self._client = client
        self._cache: dict[str, GeoPoint] = {}

    def geocode(self, query: str) -> GeoPoint:
        key = query.strip().lower()
        if key in self._cache:
            return self._cache[key]
        resp = self._client.geocode(
            QueryText=query[:200],
            MaxResults=1,
            AdditionalFeatures=["TimeZone"],
        )
        items = resp.get("ResultItems", [])
        if not items:
            raise GeocodingError(f"No geocoding result for '{query}'")
        item = items[0]
        lon, lat = item["Position"]  # Location Service returns [longitude, latitude]
        address = item.get("Address", {})
        point = GeoPoint(
            query=query,
            label=address.get("Label") or item.get("Title", query),
            lon=lon,
            lat=lat,
            country_code=(address.get("Country") or {}).get("Code2"),
            time_zone=(item.get("TimeZone") or {}).get("Name"),
        )
        self._cache[key] = point
        return point
