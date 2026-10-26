"""Unit tests for the deterministic geo-velocity engine (no AWS, no Strands needed).

    python -m unittest discover -s tests -v
"""
import unittest

from agent.geo_velocity import GeoPoint, GeocodingError, LocationGeocoder, assess, haversine_km

DUBAI_MALL = GeoPoint("Dubai Mall", "Dubai Mall, Dubai", 55.2796, 25.1972, "AE", "Asia/Dubai")
DEIRA = GeoPoint("Gold Souk", "Gold Souk, Deira", 55.2972, 25.2697, "AE", "Asia/Dubai")
ABU_DHABI = GeoPoint("Corniche", "Corniche Rd, Abu Dhabi", 54.3480, 24.4764, "AE", "Asia/Dubai")
LONDON = GeoPoint("Oxford St", "Oxford Street, London", -0.1419, 51.5154, "GB", "Europe/London")
CAIRO_AIRPORT = GeoPoint("CAI", "Cairo International Airport", 31.4056, 30.1219, "EG", "Africa/Cairo")


class HaversineTests(unittest.TestCase):
    def test_dubai_london_distance(self):
        self.assertAlmostEqual(haversine_km(DUBAI_MALL, LONDON), 5490, delta=60)

    def test_symmetry_and_zero(self):
        self.assertAlmostEqual(haversine_km(DUBAI_MALL, LONDON), haversine_km(LONDON, DUBAI_MALL))
        self.assertEqual(haversine_km(DUBAI_MALL, DUBAI_MALL), 0.0)


class AssessTests(unittest.TestCase):
    def test_impossible_travel_dubai_to_london_in_75_min(self):
        v = assess(DUBAI_MALL, "2026-10-24T04:10:00Z", LONDON, "2026-10-24T05:25:00Z")
        self.assertEqual(v.verdict, "IMPOSSIBLE")
        self.assertEqual(v.risk, "HIGH")
        self.assertGreater(v.implied_speed_kmh, 4000)

    def test_road_trip_dubai_to_abu_dhabi(self):
        v = assess(DUBAI_MALL, "2026-10-24T04:10:00Z", ABU_DHABI, "2026-10-24T07:05:00Z")
        self.assertEqual(v.verdict, "FEASIBLE_BY_GROUND")

    def test_flight_cairo_to_dubai(self):
        v = assess(CAIRO_AIRPORT, "2026-10-24T06:00:00Z", DEIRA, "2026-10-24T12:30:00Z")
        self.assertEqual(v.verdict, "FEASIBLE_BY_AIR")
        self.assertEqual(v.risk, "MEDIUM")

    def test_same_area(self):
        v = assess(DUBAI_MALL, "2026-10-24T04:10:00Z", DEIRA, "2026-10-24T04:12:00Z")
        self.assertEqual(v.verdict, "FEASIBLE_SAME_AREA")

    def test_same_timestamp_far_apart_is_impossible(self):
        v = assess(DUBAI_MALL, "2026-10-24T04:10:00Z", LONDON, "2026-10-24T04:10:00Z")
        self.assertEqual(v.verdict, "IMPOSSIBLE")
        self.assertIsNone(v.implied_speed_kmh)

    def test_order_independent(self):
        a = assess(DUBAI_MALL, "2026-10-24T04:10:00Z", LONDON, "2026-10-24T05:25:00Z")
        b = assess(LONDON, "2026-10-24T05:25:00Z", DUBAI_MALL, "2026-10-24T04:10:00Z")
        self.assertEqual(a.verdict, b.verdict)
        self.assertEqual(a.distance_km, b.distance_km)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            assess(DUBAI_MALL, "2026-10-24T04:10:00", LONDON, "2026-10-24T05:25:00Z")


class FakeGeoPlacesClient:
    """Mimics boto3 geo-places .geocode() response shape."""

    def __init__(self):
        self.calls = 0

    def geocode(self, QueryText, MaxResults, AdditionalFeatures):
        self.calls += 1
        if "nowhere" in QueryText.lower():
            return {"ResultItems": []}
        return {"ResultItems": [{
            "Title": "Dubai Mall",
            "Position": [55.2796, 25.1972],  # [lon, lat]
            "Address": {"Label": "Dubai Mall, Dubai, UAE", "Country": {"Code2": "AE"}},
            "TimeZone": {"Name": "Asia/Dubai", "Offset": "+04:00"},
        }]}


class LocationGeocoderTests(unittest.TestCase):
    def test_parses_lon_lat_and_caches(self):
        client = FakeGeoPlacesClient()
        g = LocationGeocoder(client=client)
        p = g.geocode("Dubai Mall, Dubai")
        g.geocode("  dubai mall, DUBAI ")
        self.assertEqual((p.lon, p.lat), (55.2796, 25.1972))
        self.assertEqual(p.time_zone, "Asia/Dubai")
        self.assertEqual(p.country_code, "AE")
        self.assertEqual(client.calls, 1)

    def test_no_result_raises(self):
        with self.assertRaises(GeocodingError):
            LocationGeocoder(client=FakeGeoPlacesClient()).geocode("Nowhere Land")


if __name__ == "__main__":
    unittest.main()
