from app.geo import bounding_box, haversine_m


def test_same_point_is_zero_metres():
    assert haversine_m(26.7, 88.4, 26.7, 88.4) == 0


def test_one_degree_of_latitude_is_about_111_km():
    assert 110_000 < haversine_m(26.0, 88.0, 27.0, 88.0) < 112_000


def test_known_distance_kolkata_to_howrah_station():
    # Howrah station is roughly 5 km from Kolkata's Esplanade
    distance = haversine_m(22.5645, 88.3510, 22.5839, 88.3426)
    assert 2_000 < distance < 3_000


def test_bounding_box_contains_points_inside_the_radius():
    min_lat, max_lat, min_lon, max_lon = bounding_box(26.7, 88.4, 100)
    # a point 50 m north must be inside the box
    point_lat = 26.7 + 50 / 111_000
    assert min_lat < point_lat < max_lat
    assert min_lon < 88.4 < max_lon
