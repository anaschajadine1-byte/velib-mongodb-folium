"""Accès MongoDB pour le projet Vélib."""

from __future__ import annotations

from typing import Any, Iterable

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


class MongoDBConnectionError(RuntimeError):
    pass


def get_collection(uri: str, database_name: str, collection_name: str) -> tuple[MongoClient, Collection]:
    """Connexion à MongoDB et vérification immédiate avec ``ping``."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        client.admin.command("ping")
        collection = client[database_name][collection_name]
        return client, collection
    except PyMongoError as exc:
        raise MongoDBConnectionError(
            f"Impossible de se connecter à MongoDB ({uri}). Vérifie que le serveur est démarré."
        ) from exc


def build_query(min_ebikes: int | None = None) -> dict[str, Any]:
    """Construit la requête MongoDB.

    Le filtre est appliqué directement dans ``find`` afin de limiter les
    documents transférés à Python.
    """
    if min_ebikes is None:
        return {}

    return {
        "$or": [
            {"fields.ebike": {"$gt": min_ebikes}},
            {"ebike": {"$gt": min_ebikes}},
        ]
    }


def read_documents(collection: Collection, query: dict[str, Any], limit: int = 0) -> Iterable[dict[str, Any]]:
    cursor = collection.find(query)
    if limit > 0:
        cursor = cursor.limit(limit)
    return cursor
