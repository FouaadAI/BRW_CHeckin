"""Haversine distance helpers for 200 m geofencing."""

import math

EARTH_RADIUS_METERS = 6371000


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance between two GPS points in meters."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(EARTH_RADIUS_METERS * c, 2)


def is_within_radius(
    lat1: float, lng1: float, lat2: float, lng2: float, radius_m: float = 200.0
) -> bool:
    """Return True when point 1 is within radius_m of point 2."""
    return haversine_m(lat1, lng1, lat2, lng2) <= radius_m
