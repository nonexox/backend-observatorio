import os
import json
import math
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".events_cache.json")


def _load_local_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_local_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        print(f"Aviso guardando caché local: {e}")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_lon_lat(geom: dict | None) -> tuple[float, float] | None:
    if not geom or not isinstance(geom, dict):
        return None
    coords = geom.get("coordinates")
    gtype = geom.get("type")
    if not coords:
        return None
    if gtype == "Point" and len(coords) >= 2:
        return float(coords[0]), float(coords[1])
    # Para polígonos o multipuntos, obtener el primer par [lon, lat]
    curr = coords
    while isinstance(curr, list) and curr and isinstance(curr[0], list):
        curr = curr[0]
    if isinstance(curr, list) and len(curr) >= 2:
        return float(curr[0]), float(curr[1])
    return None


def get_db_connection():
    # Timeout corto (3s) para no congelar la API si la red bloquea el puerto 5432/6543
    return psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=3)


def _upsert_via_supabase_rest(events: list) -> int:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        return 0

    url = f"{supabase_url.rstrip('/')}/rest/v1/disaster_events?on_conflict=id"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    payload = []
    for ev in events:
        payload.append({
            "id": ev["id"],
            "source": ev["source"],
            "disaster_type": ev["disaster_type"],
            "title": ev["title"],
            "severity": ev["severity"],
            "event_timestamp": ev.get("event_timestamp"),
            "raw_metrics": ev.get("raw_metrics", {}),
            "geom": ev["geom"],
        })

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code in (200, 201, 204):
        return len(payload)
    raise RuntimeError(f"Supabase REST HTTP {resp.status_code}: {resp.text}")


def upsert_events(events):
    if not events:
        return 0

    # Guardar respaldo en caché local
    cache = _load_local_cache()
    for ev in events:
        cache[ev["id"]] = ev
    _save_local_cache(cache)

    # Usar directo la vía HTTPS de Supabase sin esperar el timeout del puerto 5432
    try:
        return _upsert_via_supabase_rest(events)
    except Exception as rest_err:
        print(f"Aviso REST Supabase ({rest_err}). Eventos sincronizados en caché local ({len(events)}).")
        return len(events)


def _query_via_supabase_https(
    disaster_type: str | None = None,
    min_severity: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None
):
    rows_list = []
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if supabase_url and supabase_key:
        try:
            url = f"{supabase_url.rstrip('/')}/rest/v1/disaster_events?select=*"
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                rows_list = resp.json()
        except Exception as e:
            print(f"Aviso leyendo Supabase REST: {e}")

    if not rows_list:
        cache = _load_local_cache()
        rows_list = list(cache.values())

    features = []
    for item in rows_list:
        if disaster_type and item.get("disaster_type") != disaster_type:
            continue
        if min_severity and item.get("severity") != min_severity:
            continue

        geom = item.get("geom")
        if isinstance(geom, str):
            try:
                geom = json.loads(geom)
            except Exception:
                geom = None

        if lat is not None and lon is not None and radius_km is not None:
            pt = _extract_lon_lat(geom)
            if not pt:
                continue
            dist = _haversine_km(lat, lon, pt[1], pt[0])
            if dist > radius_km:
                continue

        ts = item.get("event_timestamp") or item.get("timestamp")
        ts_str = str(ts) if ts else None

        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "id": item.get("id"),
                "source": item.get("source"),
                "disaster_type": item.get("disaster_type"),
                "title": item.get("title"),
                "severity": item.get("severity"),
                "event_timestamp": ts_str,
                "timestamp": ts_str,
                "raw_metrics": item.get("raw_metrics"),
            }
        })

    return {"type": "FeatureCollection", "features": features}


def query_disasters(
    disaster_type: str | None = None,
    min_severity: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None
):
    # Consulta directa vía HTTPS de Supabase sin esperar el timeout del puerto 5432
    return _query_via_supabase_https(
        disaster_type=disaster_type,
        min_severity=min_severity,
        lat=lat,
        lon=lon,
        radius_km=radius_km
    )