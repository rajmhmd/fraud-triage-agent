"""v2 — THE ONE NEW TOOL: check_travel_feasibility (Amazon Location Service).

Gives the agent physical-world awareness: it geocodes two merchant locations
with Amazon Location Service, then runs a deterministic geo-velocity check.
"""
from strands import tool

from .geo_velocity import GeocodingError, LocationGeocoder, assess

_geocoder = None


def _get_geocoder():
    global _geocoder
    if _geocoder is None:
        _geocoder = LocationGeocoder()
    return _geocoder


def set_geocoder(geocoder) -> None:
    """Swap the geocoder (used by tests and the offline demo)."""
    global _geocoder
    _geocoder = geocoder


@tool
def check_travel_feasibility(
    from_location: str,
    from_timestamp_utc: str,
    to_location: str,
    to_timestamp_utc: str,
) -> dict:
    """Check whether one cardholder could physically be at two places at two times ("impossible travel").

    Use this for pairs of CARD-PRESENT transactions (channel POS_CHIP or
    POS_CONTACTLESS). Do NOT use it for ECOM / card-not-present transactions:
    the merchant's registered address says nothing about where the cardholder is.

    Locations are geocoded with Amazon Location Service; the verdict is computed
    deterministically from great-circle distance, elapsed time and realistic
    ground/air travel speeds.

    Args:
        from_location: Free-text address of the earlier merchant, e.g. "Dubai Mall, Dubai, United Arab Emirates".
        from_timestamp_utc: ISO 8601 UTC time of the earlier transaction, e.g. "2026-10-24T04:10:00Z".
        to_location: Free-text address of the later merchant.
        to_timestamp_utc: ISO 8601 UTC time of the later transaction.

    Returns:
        verdict (FEASIBLE_SAME_AREA, FEASIBLE_BY_GROUND, FEASIBLE_BY_AIR, IMPOSSIBLE),
        risk (LOW/MEDIUM/HIGH), distance_km, elapsed_hours, implied_speed_kmh,
        resolved coordinates and local time zones, and a one-line explanation.
    """
    try:
        geocoder = _get_geocoder()
        origin = geocoder.geocode(from_location)
        dest = geocoder.geocode(to_location)
        result = assess(origin, from_timestamp_utc, dest, to_timestamp_utc)
    except GeocodingError as e:
        return {"status": "error", "content": [{"text": f"Geocoding failed: {e}. Ask for a more specific address."}]}
    except ValueError as e:
        return {"status": "error", "content": [{"text": f"Bad input: {e}"}]}
    return {"status": "success", "content": [{"json": result.to_dict()}]}


GEO_TOOLS = [check_travel_feasibility]
