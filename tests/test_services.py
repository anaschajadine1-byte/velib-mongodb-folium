from pathlib import Path

from app import load_demo_documents, prepare_stations
from map_service import create_map
from mongodb_service import build_query


def test_query_without_filter():
    assert build_query() == {}


def test_query_filters_nested_and_flat_documents():
    assert build_query(10) == {
        "$or": [
            {"fields.ebike": {"$gt": 10}},
            {"ebike": {"$gt": 10}},
        ]
    }


def test_demo_pipeline_generates_map(tmp_path):
    demo_path = Path(__file__).parents[1] / "data" / "demo_stations.json"
    documents = load_demo_documents(str(demo_path))
    stations, ignored = prepare_stations(documents, origin=None, radius_m=500)
    output = tmp_path / "map.html"
    count = create_map(stations, str(output))
    html = output.read_text(encoding="utf-8")
    assert count == 3
    assert ignored == 1
    assert "Hôtel de Ville" in html
    assert "leaflet" in html.lower()
    assert "Planifier un trajet Vélib" in html
    assert "Trajet 1 — le plus rapide" in html
    assert "Trajet 2 — alternative rapide" in html
    assert "Prix estimé" not in html


def test_radius_filter():
    documents = [{"name": "Proche", "latitude": 48.8566, "longitude": 2.3522}]
    stations, ignored = prepare_stations(documents, origin=(48.8566, 2.3522), radius_m=50)
    assert len(stations) == 1
    assert ignored == 0
