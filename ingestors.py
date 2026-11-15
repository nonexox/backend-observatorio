import httpx
import os
import csv
import io
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
POLAR_WATCHLIST = ["Pine Island", "Thwaites", "Jakobshavn"]

async def fetch_gdacs_normalized():
    events = []
    url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            for feature in data.get("features", []):
                if not feature.get("geometry"):
                    continue
                props = feature["properties"]
                # Normalizar severidad (Red=alta, Orange=media, Green/other=baja)
                sev_raw = str(props.get("alertlevel", "green")).lower()
                severity = "alta" if sev_raw == "red" else "media" if sev_raw == "orange" else "baja"
                
                events.append({
                    "id": f"GDACS-{props.get('eventid')}",
                    "source": "GDACS",
                    "disaster_type": props.get("eventtype", "unknown"),
                    "title": props.get("name") or props.get("eventname") or "Alerta GDACS",
                    "severity": severity,
                    "event_timestamp": props.get("fromdate"),
                    "raw_metrics": {"url": props.get("url")},
                    "geom": feature["geometry"]
                })
        except Exception as e:
            print(f"Error descargando GDACS: {e}")
            
    return events

async def fetch_eonet_normalized():
    events = []
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100"

    async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            for ev in data.get("events", []):
                geometries = ev.get("geometry") or []
                if not geometries:
                    continue

                latest_geom = geometries[-1]
                coords = latest_geom.get("coordinates")
                if coords is None:
                    continue

                categories = ev.get("categories") or []
                cat_title = categories[0].get("title", "Evento Natural") if categories else "Evento Natural"
                cat_id = str(categories[0].get("id", "")).lower() if categories else ""

                mag_val = latest_geom.get("magnitudeValue")
                mag_unit = latest_geom.get("magnitudeUnit")

                if cat_id in ("volcanoes", "severestorms") or (isinstance(mag_val, (int, float)) and mag_val >= 50):
                    severity = "alta"
                else:
                    severity = "media"

                ts = latest_geom.get("date") or datetime.now().isoformat()

                events.append({
                    "id": str(ev.get("id")),
                    "source": "NASA_EONET",
                    "disaster_type": cat_title,
                    "title": ev.get("title", "Evento NASA EONET"),
                    "severity": severity,
                    "event_timestamp": ts,
                    "timestamp": ts,
                    "raw_metrics": {
                        "magnitudeValue": mag_val,
                        "magnitudeUnit": mag_unit,
                        "link": ev.get("link")
                    },
                    "geom": {
                        "type": latest_geom.get("type", "Point"),
                        "coordinates": coords
                    }
                })
        except Exception as e:
            print(f"Error descargando EONET: {e}")

    return events

async def fetch_firms_normalized():
    events = []
    map_key = os.getenv("NASA_FIRMS_KEY") or os.getenv("FIRMS_MAP_KEY")
    if not map_key:
        return events

    bbox = "-180,-90,180,90"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_NOAA21_NRT/{bbox}/1"

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            reader = csv.DictReader(io.StringIO(response.text))
            for row in reader:
                try:
                    frp = float(row.get("frp") or 0.0)
                except ValueError:
                    continue

                # Filtrar frp >= 10 para cubrir el planeta sin saturar con quemas menores
                if frp < 10.0:
                    continue

                conf = str(row.get("confidence", "")).lower()
                severity = "alta" if conf in ("h", "high") or frp >= 50.0 else "media"

                lat = float(row["latitude"])
                lon = float(row["longitude"])
                acq_date = row.get("acq_date", "")
                acq_time = str(row.get("acq_time", "0000")).zfill(4)
                event_ts = (
                    f"{acq_date}T{acq_time[:2]}:{acq_time[2:]}:00"
                    if acq_date
                    else datetime.now().isoformat()
                )

                events.append({
                    "id": f"FIRMS-VIIRS-{acq_date}-{acq_time}-{lat:.4f}-{lon:.4f}",
                    "source": "NASA_FIRMS",
                    "disaster_type": "Fuego",
                    "title": "Foco Térmico VIIRS_NOAA21_NRT",
                    "severity": severity,
                    "event_timestamp": event_ts,
                    "timestamp": event_ts,
                    "raw_metrics": {
                        "sensor": "VIIRS_NOAA21_NRT",
                        "confidence": conf,
                        "frp": frp,
                        "bright_ti4": row.get("bright_ti4")
                    },
                    "geom": {"type": "Point", "coordinates": [lon, lat]}
                })

                if len(events) >= 300:
                    break
        except Exception as e:
            print(f"Error descargando FIRMS: {e}")

    return events

GLACIER_COORDS = {
    "Thwaites": [-106.75, -75.05],
    "Pine Island": [-100.00, -75.15],
    "Jakobshavn": [-49.80, 69.17],
}

async def fetch_itslive_normalized():
    events = []
    ts = datetime.now().isoformat()
    for glacier in POLAR_WATCHLIST:
        coords = GLACIER_COORDS.get(glacier, [-100.00, -75.15])
        events.append({
            "id": f"ITSLIVE-{glacier.replace(' ', '')}",
            "source": "NASA_ITS_LIVE",
            "disaster_type": "Desplazamiento Hielo",
            "title": f"Monitoreo Zarr en {glacier}",
            "severity": "alta" if glacier == "Thwaites" else "media",
            "event_timestamp": ts,
            "timestamp": ts,
            "raw_metrics": {
                "glacier": glacier,
                "lon": coords[0],
                "lat": coords[1]
            },
            "geom": {"type": "Point", "coordinates": coords}
        })
    return events