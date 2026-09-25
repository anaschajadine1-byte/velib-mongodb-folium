"""Télécharge 100 stations parisiennes depuis les flux GBFS officiels Vélib."""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError


INFORMATION_URL = (
    "https://velib-metropole-opendata.smovengo.cloud/opendata/"
    "Velib_Metropole/station_information.json"
)
STATUS_URL = (
    "https://velib-metropole-opendata.smovengo.cloud/opendata/"
    "Velib_Metropole/station_status.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rafraîchit MongoDB avec un échantillon officiel de stations Vélib parisiennes."
    )
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    parser.add_argument("--database", default=os.getenv("MONGO_DB", "velib_db"))
    parser.add_argument("--collection", default=os.getenv("MONGO_COLLECTION", "velib_collection"))
    parser.add_argument("--limit", type=int, default=100, help="Nombre de stations, entre 1 et 400.")
    return parser.parse_args()


def _download(url: str) -> list[dict[str, Any]]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    stations = response.json().get("data", {}).get("stations")
    if not isinstance(stations, list):
        raise RuntimeError(f"Réponse GBFS inattendue : {url}")
    return stations


def _arrondissement(station_code: Any) -> int | None:
    code = str(station_code or "")
    if not code.isdigit():
        return None
    # Les codes parisiens suivent le modèle arrondissement * 1000 + station.
    # Exemples : 1001 -> 1er, 16107 -> 16e.
    value = int(code) // 1000
    return value if 1 <= value <= 20 else None


def _bike_counts(status: dict[str, Any]) -> tuple[int, int]:
    mechanical = 0
    ebike = 0
    for item in status.get("num_bikes_available_types", []):
        if isinstance(item, dict):
            mechanical += int(item.get("mechanical", 0) or 0)
            ebike += int(item.get("ebike", 0) or 0)
    return mechanical, ebike


def build_documents(limit: int) -> list[dict[str, Any]]:
    information = _download(INFORMATION_URL)
    statuses = _download(STATUS_URL)
    status_by_id = {str(item.get("station_id")): item for item in statuses}
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for info in information:
        arrondissement = _arrondissement(info.get("stationCode"))
        status = status_by_id.get(str(info.get("station_id")))
        if arrondissement is None or status is None:
            continue
        try:
            latitude = float(info["lat"])
            longitude = float(info["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        mechanical, ebike = _bike_counts(status)
        last_reported = status.get("last_reported")
        last_update = None
        if isinstance(last_reported, (int, float)) and last_reported > 0:
            last_update = datetime.fromtimestamp(last_reported, timezone.utc).isoformat()

        groups[arrondissement].append(
            {
                "fields": {
                    "stationcode": str(info.get("stationCode", "")),
                    "name": str(info.get("name") or "Station sans nom"),
                    "coordonnees_geo": [latitude, longitude],
                    "ebike": ebike,
                    "mechanical": mechanical,
                    "numbikesavailable": int(status.get("num_bikes_available", 0) or 0),
                    "numdocksavailable": int(status.get("num_docks_available", 0) or 0),
                    "capacity": int(info.get("capacity", 0) or 0),
                    "is_renting": bool(status.get("is_renting", 0)),
                    "is_returning": bool(status.get("is_returning", 0)),
                    "last_update": last_update,
                    "arrondissement": arrondissement,
                },
                "source": "Vélib’ Métropole — flux GBFS officiel",
                "snapshot_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    for stations in groups.values():
        stations.sort(key=lambda item: item["fields"]["name"].casefold())

    # Tour par tour des arrondissements pour obtenir une carte bien répartie.
    selected: list[dict[str, Any]] = []
    row = 0
    while len(selected) < limit:
        added = False
        for arrondissement in range(1, 21):
            stations = groups.get(arrondissement, [])
            if row < len(stations):
                selected.append(stations[row])
                added = True
                if len(selected) == limit:
                    break
        if not added:
            break
        row += 1
    return selected


def main() -> int:
    args = parse_args()
    if not 1 <= args.limit <= 400:
        print("Erreur : limit doit être compris entre 1 et 400.", file=sys.stderr)
        return 2

    try:
        documents = build_documents(args.limit)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"Erreur de téléchargement : {exc}", file=sys.stderr)
        return 2
    if len(documents) < args.limit:
        print(f"Erreur : seulement {len(documents)} stations exploitables reçues.", file=sys.stderr)
        return 2

    client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=4000)
    try:
        client.admin.command("ping")
        collection = client[args.database][args.collection]
        # La suppression ne concerne que la collection explicitement sélectionnée.
        collection.delete_many({})
        collection.insert_many(documents)
        print(f"Rafraîchissement réussi : {len(documents)} stations officielles chargées.")
        print(f"Destination : {args.database}.{args.collection}")
        print("Répartition : arrondissements 1 à 20.")
        return 0
    except PyMongoError as exc:
        print(f"Erreur MongoDB : {exc}", file=sys.stderr)
        return 3
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
