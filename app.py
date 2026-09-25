"""Projet Vélib : MongoDB + PyMongo + Folium.

Usage simple :
    python app.py

Filtre MongoDB sur les vélos électriques :
    python app.py --min-ebikes 10

Extension du support fourni :
    python app.py --address "10 rue de Rivoli, Paris" --radius 500
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any

from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim

from map_service import create_map
from mongodb_service import MongoDBConnectionError, build_query, get_collection, read_documents
from station_utils import Station, normalize_station


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Affiche les stations Vélib stockées dans MongoDB sur une carte Folium."
    )
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    parser.add_argument("--database", default=os.getenv("MONGO_DB", "velib_db"))
    parser.add_argument("--collection", default=os.getenv("MONGO_COLLECTION", "velib_collection"))
    parser.add_argument(
        "--min-ebikes",
        type=int,
        default=None,
        help="N'afficher que les stations ayant PLUS de N vélos électriques.",
    )
    parser.add_argument(
        "--address",
        default=None,
        help="Extension : adresse autour de laquelle chercher les stations.",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=500,
        help="Extension : rayon en mètres autour de l'adresse (défaut: 500).",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limiter le nombre de documents lus (0 = sans limite).")
    parser.add_argument("--output", default="map_velib.html", help="Nom du fichier HTML généré.")
    parser.add_argument("--no-open", action="store_true", help="Ne pas ouvrir automatiquement la carte.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Utiliser le petit jeu de démonstration fourni, sans se connecter à MongoDB.",
    )
    parser.add_argument(
        "--demo-file",
        default=str(Path(__file__).with_name("data") / "demo_stations.json"),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def geocode_address(address: str) -> tuple[float, float]:
    geolocator = Nominatim(user_agent="projet_velib_mongodb_folium")
    try:
        location = geolocator.geocode(address, timeout=10)
    except GeocoderServiceError as exc:
        raise RuntimeError("Le service de géocodage n'est pas disponible pour le moment.") from exc

    if location is None:
        raise RuntimeError(f"Adresse introuvable : {address}")
    return float(location.latitude), float(location.longitude)


def prepare_stations(
    documents,
    origin: tuple[float, float] | None,
    radius_m: int,
) -> tuple[list[tuple[Station, float | None]], int]:
    stations: list[tuple[Station, float | None]] = []
    ignored = 0

    for document in documents:
        station = normalize_station(document)
        if station is None:
            ignored += 1
            continue

        distance_m: float | None = None
        if origin is not None:
            distance_m = geodesic(origin, (station.latitude, station.longitude)).meters
            if distance_m > radius_m:
                continue

        stations.append((station, distance_m))

    return stations, ignored


def load_demo_documents(path: str) -> list[dict[str, Any]]:
    """Charge uniquement le jeu de démonstration explicitement demandé."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Impossible de lire le jeu de démonstration : {path}") from exc
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise RuntimeError("Le jeu de démonstration doit être une liste de documents JSON.")
    return data


def main() -> int:
    args = parse_args()

    if args.radius <= 0 or args.limit < 0 or (args.min_ebikes is not None and args.min_ebikes < 0):
        print("Erreur : radius doit être positif; limit et min-ebikes doivent être positifs ou nuls.", file=sys.stderr)
        return 2

    origin = None
    if args.address:
        try:
            origin = geocode_address(args.address)
            print(f"Adresse trouvée : latitude={origin[0]:.6f}, longitude={origin[1]:.6f}")
        except RuntimeError as exc:
            print(f"Erreur : {exc}", file=sys.stderr)
            return 2

    client = None
    try:
        query = build_query(args.min_ebikes)
        if args.demo:
            documents = load_demo_documents(args.demo_file)
            if args.min_ebikes is not None:
                documents = [
                    document
                    for document in documents
                    if (station := normalize_station(document)) is not None
                    and station.ebike > args.min_ebikes
                ]
            if args.limit > 0:
                documents = documents[: args.limit]
            print("Mode DÉMONSTRATION : aucun accès à MongoDB.")
            print(f"Fichier : {Path(args.demo_file).resolve()}")
        else:
            try:
                client, collection = get_collection(args.mongo_uri, args.database, args.collection)
            except MongoDBConnectionError as exc:
                print(f"Erreur : {exc}", file=sys.stderr)
                return 3
            print(f"MongoDB : {args.database}.{args.collection}")
            print(f"Requête find() : {query or '{}'}")
            documents = read_documents(collection, query, args.limit)

        stations, ignored = prepare_stations(documents, origin, args.radius)

        count = create_map(
            stations,
            args.output,
            center=origin,
            origin_label=args.address,
        )

        output_file = Path(args.output).resolve()
        print(f"Stations affichées : {count}")
        if ignored:
            print(f"Documents ignorés (coordonnées invalides/manquantes) : {ignored}")
        print(f"Carte générée : {output_file}")

        if not args.no_open:
            webbrowser.open(output_file.as_uri())
        return 0
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
