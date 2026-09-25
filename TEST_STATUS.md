# État des tests

Validation effectuée le 24 septembre 2026 sous Windows avec Python 3.11.9.

| Composant | Statut | Comment testé | Limitation restante |
|---|---|---|---|
| Syntaxe et imports | Réussi | `compileall` dans un environnement virtuel propre | Aucune observée |
| Normalisation des stations | Réussi | Tests documents imbriqués, plats, GeoJSON et valeurs numériques texte | D'autres schémas réels pourraient demander une adaptation |
| Coordonnées invalides | Réussi | Tests de coordonnées absentes et hors limites | Documents invalides volontairement ignorés |
| Construction du filtre | Réussi | Test exact de la requête `$or` / `$gt` | Les valeurs MongoDB doivent être numériques pour `$gt` |
| Génération Folium | Réussi | HTML créé et contenu Leaflet/marqueurs vérifié | Les tuiles nécessitent Internet à l'affichage |
| Mode démo complet | Réussi | 3 stations affichées, 1 document invalide ignoré | Jeu synthétique, pas données de rendu |
| Filtre démo `> 10` | Réussi | 2 stations affichées | Sert seulement à la validation locale |
| Connexion MongoDB réelle | Réussi | `ping` et exécution de l'application sur `localhost:27017` | Aucune observée |
| Données officielles dans MongoDB | Réussi | 100 stations GBFS chargées dans `velib_db.velib_collection` | Instantané, à rafraîchir pour de nouvelles valeurs |
| Répartition géographique | Réussi | 5 stations dans chacun des 20 arrondissements | Échantillon, pas les 1 500 stations du réseau |
| Filtre MongoDB réel `> 10` | Réussi | Requête `$gt` exécutée dans MongoDB | Le nombre varie avec la disponibilité du moment |
| Adresse / GeoPy | Réussi | Géocodage réel de « 10 rue de Rivoli, 75004 Paris » et carte générée | Dépend de Nominatim et d'Internet |
| Planificateur interactif | Réussi | Deux clics réels dans le navigateur : sélection des stations, matrices de durée OSRM et trajet le plus rapide suivant les rues | Dépend du service OSRM et d'Internet ; pas de trafic en temps réel |
| Résultat global automatisé | Réussi | `pytest` : **9 tests réussis** | Aucune observée sur l'instantané testé |
