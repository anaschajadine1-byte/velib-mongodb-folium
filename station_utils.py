"""Normalisation et validation des documents Vélib stockés dans MongoDB."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class Station:
    name: str
    latitude: float
    longitude: float
    ebike: int = 0
    mechanical: int = 0
    docks_available: int = 0
    station_code: str = ""
    capacity: int = 0
    is_renting: bool = True
    last_update: str = ""


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _extract_coordinates(data: Mapping[str, Any]) -> Optional[tuple[float, float]]:
    """Retourne (latitude, longitude) à partir des champs vus dans le support."""
    coords = data.get("coordonnees_geo")

    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
        try:
            return float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            pass

    if isinstance(coords, Mapping):
        # Variante GeoJSON : coordinates est dans l'ordre longitude, latitude.
        geojson_coords = coords.get("coordinates")
        if isinstance(geojson_coords, (list, tuple)) and len(geojson_coords) >= 2:
            try:
                return float(geojson_coords[1]), float(geojson_coords[0])
            except (TypeError, ValueError):
                pass
        lat = coords.get("lat", coords.get("latitude"))
        lon = coords.get("lon", coords.get("lng", coords.get("longitude")))
        if lat is not None and lon is not None:
            try:
                return float(lat), float(lon)
            except (TypeError, ValueError):
                pass

    lat = data.get("latitude", data.get("lat"))
    lon = data.get("longitude", data.get("lon", data.get("lng")))
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None

    return None


def normalize_station(document: Mapping[str, Any]) -> Optional[Station]:
    """Transforme un document MongoDB brut en Station exploitable par Folium.

    Le support fourni place les informations de station sous la clé ``fields``.
    La fonction accepte aussi un document déjà aplati afin de rendre le projet
    plus tolérant aux variantes d'import MongoDB.
    """
    payload = document.get("fields") if isinstance(document.get("fields"), Mapping) else document

    coords = _extract_coordinates(payload)
    if coords is None:
        return None

    latitude, longitude = coords
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None

    name = str(payload.get("name") or payload.get("nom") or "Station sans nom").strip()
    if not name:
        name = "Station sans nom"

    return Station(
        name=name,
        latitude=latitude,
        longitude=longitude,
        ebike=_as_int(payload.get("ebike")),
        mechanical=_as_int(payload.get("mechanical")),
        docks_available=_as_int(payload.get("numdocksavailable", payload.get("docks_available"))),
        station_code=str(payload.get("stationcode") or payload.get("stationCode") or ""),
        capacity=_as_int(payload.get("capacity")),
        is_renting=bool(payload.get("is_renting", True)),
        last_update=str(payload.get("last_update") or ""),
    )
