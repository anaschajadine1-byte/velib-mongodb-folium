from station_utils import normalize_station


def test_nested_document_is_normalized():
    station = normalize_station(
        {
            "fields": {
                "name": "Test",
                "coordonnees_geo": [48.85, 2.35],
                "ebike": "7",
                "mechanical": 2,
                "numdocksavailable": None,
            }
        }
    )
    assert station is not None
    assert (station.latitude, station.longitude) == (48.85, 2.35)
    assert station.ebike == 7
    assert station.docks_available == 0


def test_flat_and_geojson_documents_are_supported():
    station = normalize_station(
        {"nom": "GeoJSON", "coordonnees_geo": {"coordinates": [2.3, 48.8]}}
    )
    assert station is not None
    assert (station.latitude, station.longitude) == (48.8, 2.3)


def test_invalid_coordinates_are_rejected():
    assert normalize_station({"fields": {"name": "Sans coordonnées"}}) is None
    assert normalize_station({"latitude": 120, "longitude": 2.3}) is None
