"""Création de la carte Folium et des marqueurs Vélib."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Iterable

import folium
from folium.plugins import MarkerCluster

from station_utils import Station


PARIS_CENTER = (48.8566, 2.3522)


def _trip_planner_html(map_name: str, stations: list[tuple[Station, float | None]]) -> str:
    """Retourne le panneau et le JavaScript du planificateur routier."""
    station_data = [
        {
            "name": station.name,
            "lat": station.latitude,
            "lon": station.longitude,
            "bikes": station.ebike + station.mechanical,
            "ebikes": station.ebike,
            "mechanical": station.mechanical,
            "docks": station.docks_available,
            "renting": station.is_renting,
        }
        for station, _ in stations
    ]
    safe_json = json.dumps(station_data, ensure_ascii=False).replace("</", "<\\/")
    return f"""
    <div id="trip-planner" style="position:fixed; top:12px; left:58px; z-index:10000;
         width:330px; max-height:calc(100vh - 35px); overflow:auto; background:#fff;
         padding:14px; border-radius:10px; box-shadow:0 3px 15px rgba(0,0,0,.28);
         font:14px Arial,sans-serif; color:#222;">
      <div style="font-size:18px; font-weight:bold; color:#1677c8; margin-bottom:6px;">
        Planifier un trajet Vélib’
      </div>
      <div id="planner-help" style="line-height:1.4; margin-bottom:10px;">
        1. Cliquez sur votre départ.<br>2. Cliquez sur votre destination.
      </div>
      <button id="reset-trip" type="button" style="padding:7px 9px; cursor:pointer;">
        Recommencer
      </button>
      <div id="planner-result" style="margin-top:10px; line-height:1.45;"></div>
      <div style="font-size:11px; color:#666; margin-top:9px;">
        Les parcours suivent les rues OpenStreetMap. Le calcul nécessite une
        connexion Internet au service de routage OSRM.
      </div>
    </div>
    <script>
    window.addEventListener('load', function () {{
      const plannerMap = {map_name};
      const stations = {safe_json};
      let startPoint = null;
      let endPoint = null;
      let startMarker = null;
      let endMarker = null;
      let routeLayers = [];
      let calculationToken = 0;
      const help = document.getElementById('planner-help');
      const result = document.getElementById('planner-result');
      const routingEndpoints = {{
        foot: 'https://routing.openstreetmap.de/routed-foot',
        bike: 'https://routing.openstreetmap.de/routed-bike'
      }};

      function escapeHtml(value) {{
        const div = document.createElement('div');
        div.textContent = String(value);
        return div.innerHTML;
      }}

      function distanceMeters(a, b) {{
        const radius = 6371000;
        const toRad = value => value * Math.PI / 180;
        const dLat = toRad(b.lat - a.lat);
        const dLon = toRad(b.lng - a.lng);
        const lat1 = toRad(a.lat);
        const lat2 = toRad(b.lat);
        const h = Math.sin(dLat / 2) ** 2 +
          Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
        return 2 * radius * Math.asin(Math.sqrt(h));
      }}

      function stationPoint(station) {{
        return {{lat: station.lat, lng: station.lon}};
      }}

      function nearestStations(point, predicate, count) {{
        return stations
          .filter(predicate)
          .map(station => ({{
            station: station,
            distance: distanceMeters(point, stationPoint(station))
          }}))
          .sort((a, b) => a.distance - b.distance)
          .slice(0, count);
      }}

      function coordinateString(points) {{
        return points
          .map(point => point.lng.toFixed(6) + ',' + point.lat.toFixed(6))
          .join(';');
      }}

      async function fetchRoutingJson(url) {{
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 15000);
        try {{
          const response = await fetch(url, {{signal: controller.signal}});
          if (!response.ok) throw new Error('HTTP ' + response.status);
          const data = await response.json();
          if (data.code !== 'Ok') throw new Error(data.message || data.code);
          return data;
        }} finally {{
          window.clearTimeout(timeout);
        }}
      }}

      async function routingTable(mode, points, sources, destinations) {{
        const url = routingEndpoints[mode] + '/table/v1/driving/' +
          coordinateString(points) +
          '?sources=' + encodeURIComponent(sources.join(';')) +
          '&destinations=' + encodeURIComponent(destinations.join(';')) +
          '&annotations=duration,distance';
        return fetchRoutingJson(url);
      }}

      async function routedPath(mode, from, to) {{
        const url = routingEndpoints[mode] + '/route/v1/driving/' +
          coordinateString([from, to]) +
          '?overview=full&geometries=geojson&steps=false&alternatives=false';
        const data = await fetchRoutingJson(url);
        const route = data.routes[0];
        if (!route) return null;
        return {{
          distance: route.distance,
          duration: route.duration,
          coordinates: route.geometry.coordinates.map(coord => [coord[1], coord[0]])
        }};
      }}

      function clearRoute() {{
        routeLayers.forEach(layer => plannerMap.removeLayer(layer));
        routeLayers = [];
      }}

      function resetTrip() {{
        calculationToken += 1;
        clearRoute();
        if (startMarker) plannerMap.removeLayer(startMarker);
        if (endMarker) plannerMap.removeLayer(endMarker);
        startMarker = null;
        endMarker = null;
        startPoint = null;
        endPoint = null;
        result.innerHTML = '';
        help.innerHTML = '1. Cliquez sur votre départ.<br>2. Cliquez sur votre destination.';
      }}

      function setStart(latlng) {{
        resetTrip();
        startPoint = latlng;
        startMarker = L.marker(latlng, {{
          icon: L.icon({{
            iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-violet.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
            iconSize: [25, 41], iconAnchor: [12, 41]
          }})
        }}).addTo(plannerMap).bindTooltip('Votre départ').openTooltip();
        help.innerHTML = '<strong>Départ enregistré.</strong><br>Cliquez maintenant sur la destination.';
      }}

      async function buildRoutedPlan(candidate) {{
        const departurePoint = stationPoint(candidate.departure.station);
        const arrivalPoint = stationPoint(candidate.arrival.station);
        const [walkStart, bike, walkEnd] = await Promise.all([
          routedPath('foot', startPoint, departurePoint),
          routedPath('bike', departurePoint, arrivalPoint),
          routedPath('foot', arrivalPoint, endPoint)
        ]);
        if (!walkStart || !walkEnd || !bike) return null;
        return {{
          departure: candidate.departure,
          arrival: candidate.arrival,
          walkStart: walkStart,
          bike: bike,
          walkEnd: walkEnd,
          walkingSeconds: walkStart.duration + walkEnd.duration,
          cyclingSeconds: bike.duration,
          totalSeconds: walkStart.duration + bike.duration + walkEnd.duration
        }};
      }}

      async function calculatePlan() {{
        const token = ++calculationToken;
        clearRoute();
        result.innerHTML = '<strong>Calcul de l’itinéraire dans les rues…</strong>';
        const departures = nearestStations(
          startPoint,
          station => station.renting && station.bikes > 0,
          6
        );
        const arrivals = nearestStations(
          endPoint,
          station => station.docks > 0,
          6
        );
        if (!departures.length) {{
          result.innerHTML = '<strong>Aucune station avec vélo disponible.</strong>';
          return;
        }}
        if (!arrivals.length) {{
          result.innerHTML = '<strong>Aucune station d’arrivée avec dock disponible.</strong>';
          return;
        }}

        try {{
          const points = [
            startPoint,
            ...departures.map(item => stationPoint(item.station)),
            ...arrivals.map(item => stationPoint(item.station)),
            endPoint
          ];
          const departureIndexes = departures.map((_, index) => index + 1);
          const arrivalOffset = 1 + departures.length;
          const arrivalIndexes = arrivals.map((_, index) => arrivalOffset + index);
          const endIndex = points.length - 1;

          const [footTable, bikeTable] = await Promise.all([
            routingTable(
              'foot',
              points,
              [0, ...arrivalIndexes],
              [...departureIndexes, endIndex]
            ),
            routingTable('bike', points, departureIndexes, arrivalIndexes)
          ]);

          const candidates = [];
          departures.forEach((departure, departureIndex) => {{
            arrivals.forEach((arrival, arrivalIndex) => {{
              if (departure.station.name === arrival.station.name) return;
              const walkToBike = footTable.durations[0][departureIndex];
              const bikeDuration = bikeTable.durations[departureIndex][arrivalIndex];
              const walkFromBike = footTable.durations[arrivalIndex + 1][departures.length];
              if (walkToBike == null || bikeDuration == null || walkFromBike == null) return;
              candidates.push({{
                departure: departure,
                arrival: arrival,
                tableDuration: walkToBike + bikeDuration + walkFromBike
              }});
            }});
          }});
          candidates.sort((a, b) => a.tableDuration - b.tableDuration);
          if (!candidates.length) throw new Error('Aucune combinaison routable');

          const plan = await buildRoutedPlan(candidates[0]);
          if (token !== calculationToken) return;
          if (!plan) throw new Error('Aucun itinéraire détaillé disponible');

          const color = '#1677c8';
          const bounds = [startPoint, endPoint];
          routeLayers.push(
            L.polyline(plan.walkStart.coordinates, {{color:color, dashArray:'6,7', weight:6, opacity:0.95}}).addTo(plannerMap),
            L.polyline(plan.bike.coordinates, {{color:color, weight:6, opacity:0.95}}).addTo(plannerMap),
            L.polyline(plan.walkEnd.coordinates, {{color:color, dashArray:'6,7', weight:6, opacity:0.95}}).addTo(plannerMap)
          );
          bounds.push(...plan.walkStart.coordinates, ...plan.bike.coordinates, ...plan.walkEnd.coordinates);
          plannerMap.fitBounds(L.latLngBounds(bounds), {{padding:[60,60]}});

          const walkingMinutes = Math.max(1, Math.round(plan.walkingSeconds / 60));
          const cyclingMinutes = Math.max(1, Math.round(plan.cyclingSeconds / 60));
          const totalMinutes = Math.max(1, Math.round(plan.totalSeconds / 60));
          help.innerHTML = '<strong>Itinéraire routier calculé.</strong> Le tracé bleu suit les rues. Les traits pointillés représentent la marche.';
          result.innerHTML = '<div style="border-left:5px solid ' + color + ';padding:7px 8px;margin:8px 0;background:#f7f7f7">' +
            '<strong>Trajet le plus rapide</strong><br>' +
            'Départ : ' + escapeHtml(plan.departure.station.name) +
            ' (' + plan.departure.station.bikes + ' vélo(x))<br>' +
            'Arrivée : ' + escapeHtml(plan.arrival.station.name) +
            ' (' + plan.arrival.station.docks + ' dock(s))<br>' +
            'Marche : ' + walkingMinutes + ' min — Vélo : ' +
            cyclingMinutes + ' min (' + (plan.bike.distance / 1000).toFixed(1) + ' km)<br>' +
            '<strong>Durée totale : ' + totalMinutes + ' min</strong></div>';
        }} catch (error) {{
          if (token !== calculationToken) return;
          console.error('Erreur de routage OSRM', error);
          help.innerHTML = '<strong>Le service de routage ne répond pas.</strong>';
          result.innerHTML = 'Vérifiez la connexion Internet puis cliquez sur « Recommencer ».';
        }}
      }}

      function setDestination(latlng) {{
        endPoint = latlng;
        endMarker = L.marker(latlng).addTo(plannerMap).bindTooltip('Votre destination').openTooltip();
        help.innerHTML = '<strong>Destination enregistrée.</strong><br>Calcul du trajet dans les rues…';
        calculatePlan();
      }}

      plannerMap.on('click', function (event) {{
        if (!startPoint) setStart(event.latlng);
        else if (!endPoint) setDestination(event.latlng);
      }});

      document.getElementById('reset-trip').addEventListener('click', resetTrip);
    }});
    </script>
    """


def _popup_html(station: Station, distance_m: float | None = None) -> str:
    distance_line = ""
    if distance_m is not None:
        distance_line = f'<p><strong>Distance :</strong> {int(distance_m)} m</p>'

    street_view_url = (
        "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint="
        f"{station.latitude},{station.longitude}"
    )
    total_bikes = station.ebike + station.mechanical
    code_line = f"<p><strong>Code station :</strong> {escape(station.station_code)}</p>" if station.station_code else ""
    capacity_line = f"<p><strong>Capacité :</strong> {station.capacity}</p>" if station.capacity else ""
    status_text = "Ouverte à la location" if station.is_renting else "Location indisponible"
    update_line = f"<p><strong>Dernière mise à jour :</strong> {escape(station.last_update)}</p>" if station.last_update else ""

    return f"""
    <div style="font-family:Arial,sans-serif; min-width:250px;">
      <h3 style="margin:0 0 10px 0;">{escape(station.name)}</h3>
      {code_line}
      <p><strong>État :</strong> {status_text}</p>
      <p><strong>Total des vélos :</strong> {total_bikes}</p>
      <p><strong>Vélos électriques :</strong> {station.ebike}</p>
      <p><strong>Vélos mécaniques :</strong> {station.mechanical}</p>
      <p><strong>Docks disponibles :</strong> {station.docks_available}</p>
      {capacity_line}
      {update_line}
      {distance_line}
      <a href="{street_view_url}" target="_blank">Voir dans Street View</a>
    </div>
    """


def create_map(
    stations: Iterable[tuple[Station, float | None]],
    output_path: str,
    center: tuple[float, float] | None = None,
    origin_label: str | None = None,
) -> int:
    """Crée la carte HTML et retourne le nombre de stations affichées."""
    station_items = list(stations)
    map_center = center or PARIS_CENTER

    m = folium.Map(location=list(map_center), zoom_start=13, tiles="OpenStreetMap", control_scale=True)

    # Fond satellite gratuit, en complément du fond OpenStreetMap.
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Tiles © Esri",
        name="Esri Satellite",
        max_zoom=19,
    ).add_to(m)

    if center is not None and origin_label:
        folium.Marker(
            location=list(center),
            tooltip=origin_label,
            popup=folium.Popup(f"<strong>{escape(origin_label)}</strong>", max_width=300),
            icon=folium.Icon(color="green", icon="home"),
        ).add_to(m)

    cluster = MarkerCluster(name="Stations Vélib").add_to(m)
    bounds: list[list[float]] = []

    for station, distance_m in station_items:
        bounds.append([station.latitude, station.longitude])
        total_bikes = station.ebike + station.mechanical
        if not station.is_renting:
            marker_color = "gray"
        elif total_bikes >= 10:
            marker_color = "green"
        elif total_bikes > 0:
            marker_color = "orange"
        else:
            marker_color = "red"

        folium.Marker(
            location=[station.latitude, station.longitude],
            tooltip=station.name,
            popup=folium.Popup(_popup_html(station, distance_m), max_width=350),
            icon=folium.Icon(color=marker_color, icon="info-sign"),
        ).add_to(cluster)

    if not station_items:
        folium.Marker(
            location=list(map_center),
            tooltip="Aucune station trouvée",
            popup=folium.Popup(
                "<strong>Aucune station ne correspond à la requête.</strong>",
                max_width=320,
            ),
            icon=folium.Icon(color="lightgray", icon="info-sign"),
        ).add_to(m)

    if center is not None:
        bounds.append([center[0], center[1]])

    if len(bounds) >= 2:
        m.fit_bounds(bounds, padding=(25, 25))

    folium.LayerControl().add_to(m)
    legend = """
    <div style="position:fixed; bottom:30px; left:30px; z-index:9999;
                background:white; padding:10px 14px; border:2px solid #777;
                border-radius:6px; font:14px Arial;">
      <strong>Disponibilité</strong><br>
      <span style="color:green;">●</span> 10 vélos ou plus<br>
      <span style="color:orange;">●</span> 1 à 9 vélos<br>
      <span style="color:red;">●</span> aucun vélo<br>
      <span style="color:gray;">●</span> station indisponible
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend))
    if station_items:
        m.get_root().html.add_child(
            folium.Element(_trip_planner_html(m.get_name(), station_items))
        )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    return len(station_items)
