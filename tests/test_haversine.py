"""Unit tests for Haversine distance helpers."""

import math

import pytest

from src.haversine import EARTH_RADIUS_METERS, haversine_m, is_within_radius


ALEXANDERPLATZ = (52.521585, 13.413908)


def test_same_point_returns_zero():
    lat, lng = ALEXANDERPLATZ
    assert haversine_m(lat, lng, lat, lng) == 0.0


def test_is_within_radius_same_point():
    lat, lng = ALEXANDERPLATZ
    assert is_within_radius(lat, lng, lat, lng) is True


def test_exactly_200m_boundary():
    """Move north by exactly 200 m using the inverse Haversine formula."""
    lat, lng = ALEXANDERPLATZ
    # Δφ = 2 * asin(sin(distance / (2 * R)))  [radians]
    delta_phi_rad = 2 * math.asin(math.sin(100.0 / EARTH_RADIUS_METERS))
    offset = math.degrees(delta_phi_rad)
    distance = haversine_m(lat, lng, lat + offset, lng)
    assert abs(distance - 200.0) < 0.01
    assert is_within_radius(lat, lng, lat + offset, lng) is True


def test_less_than_200m():
    lat, lng = ALEXANDERPLATZ
    offset = 100.0 / 111_000.0
    distance = haversine_m(lat, lng, lat + offset, lng)
    assert distance < 200.0
    assert is_within_radius(lat, lng, lat + offset, lng) is True


def test_more_than_200m():
    lat, lng = ALEXANDERPLATZ
    offset = 300.0 / 111_000.0
    distance = haversine_m(lat, lng, lat + offset, lng)
    assert distance > 200.0
    assert is_within_radius(lat, lng, lat + offset, lng) is False


def test_earth_radius_constant():
    assert EARTH_RADIUS_METERS == 6371000


def test_symmetry():
    a, b = ALEXANDERPLATZ
    c, d = (52.520112, 13.372955)  # Bundestag
    assert haversine_m(a, b, c, d) == haversine_m(c, d, a, b)
