"""Importe le jeu de démonstration dans MongoDB sans écraser de données."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Charge les stations de test dans MongoDB.")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    parser.add_argument("--database", default=os.getenv("MONGO_DB", "velib_db"))
    parser.add_argument("--collection", default=os.getenv("MONGO_COLLECTION", "velib_collection"))
    parser.add_argument(
        "--file",
        default=str(Path(__file__).with_name("data") / "demo_stations.json"),
        help="Fichier JSON à importer.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        documents = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Erreur de lecture du fichier : {exc}", file=sys.stderr)
        return 2

    if not isinstance(documents, list) or not documents or not all(isinstance(item, dict) for item in documents):
        print("Erreur : le fichier doit contenir une liste non vide de documents JSON.", file=sys.stderr)
        return 2

    client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=4000)
    try:
        client.admin.command("ping")
        collection = client[args.database][args.collection]
        existing = collection.count_documents({})
        if existing:
            print(
                f"Import annulé : {args.database}.{args.collection} contient déjà {existing} document(s)."
            )
            print("Aucune donnée existante n'a été modifiée.")
            return 1

        result = collection.insert_many(documents)
        print(f"Import réussi : {len(result.inserted_ids)} documents de test ajoutés.")
        print(f"Destination : {args.database}.{args.collection}")
        return 0
    except PyMongoError as exc:
        print(f"Erreur MongoDB : {exc}", file=sys.stderr)
        return 3
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
