import asf_search
from datetime import datetime, timedelta, timezone
try:
    import ee
except ImportError:
    ee = None

_ee_initialized = False

def search_sar_granules(
    lat: float,
    lon: float,
    days_back: int = 60,
    max_results: int = 10
):
    """
    Busca escenas SAR (NISAR Banda L, Sentinel-1 Banda C y ALOS PALSAR Banda L) en el catálogo de ASF
    que intersecten el punto (lat, lon), descartando archivos crudos L0 y conservando solo escenas
    con imagen previa (browse_url PNG/JPG) lista para pintar en el mapa.
    """
    wkt_point = f"POINT({lon} {lat})"
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    platforms = [
        asf_search.PLATFORM.NISAR,
        asf_search.PLATFORM.SENTINEL1,
        asf_search.PLATFORM.ALOS,
    ]

    features = []
    try:
        # Pedimos un lote mayor para filtrar niveles L0 y escenas sin imagen browse
        results = asf_search.geo_search(
            intersectsWith=wkt_point,
            platform=platforms,
            start=start_date,
            end=end_date,
            maxResults=max(max_results * 6, 50),
        )

        for item in results:
            props = item.properties or {}
            proc_level = str(props.get("processingLevel") or "").upper()
            scene_name = str(props.get("sceneName") or "")

            # Descartar archivos crudos nivel L0 / RAW
            if "L0" in proc_level or "RAW" in proc_level or "_RAW_" in scene_name.upper():
                continue

            browse_raw = props.get("browse") or []
            browse_list = (
                [u for u in browse_raw if isinstance(u, str) and "no-browse" not in u.lower()]
                if isinstance(browse_raw, list)
                else ([browse_raw] if isinstance(browse_raw, str) and "no-browse" not in browse_raw.lower() else [])
            )

            # Conservar solo escenas con browse_url válido (preferiblemente PNG)
            png_urls = [u for u in browse_list if u.lower().endswith(".png")]
            browse_url = png_urls[0] if png_urls else (browse_list[0] if browse_list else None)
            if not browse_url or not browse_url.startswith("http"):
                continue

            features.append({
                "type": "Feature",
                "geometry": item.geometry,
                "properties": {
                    "sceneName": props.get("sceneName"),
                    "platform": props.get("platform"),
                    "processingLevel": props.get("processingLevel"),
                    "beamModeType": props.get("beamModeType"),
                    "polarization": props.get("polarization"),
                    "startTime": props.get("startTime"),
                    "browse": browse_list,
                    "browse_url": browse_url,
                    "url": props.get("url"),
                }
            })

            if len(features) >= max_results:
                break
    except Exception as e:
        print(f"Error consultando catálogo SAR de ASF: {e}")

    return {
        "type": "FeatureCollection",
        "features": features
    }

def init_ee():
    global _ee_initialized
    if not _ee_initialized:
        try:
            # Inicializa Earth Engine. Requiere autenticación previa.
            ee.Initialize()
            _ee_initialized = True
        except Exception as e:
            print(f"Error inicializando Earth Engine: {e}")

def get_historical_tiles(lat: float, lon: float, date_before: str, date_after: str):
    init_ee()
    
    # Crear la geometría del punto consultado
    point = ee.Geometry.Point([lon, lat])
    
    # 1. Capa SAR (Sentinel-1 GRD / Proxy para NISAR)
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(point) \
        .filterDate(date_before, date_after) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
        .select('VV') \
        .median()
        
    # 2. Capa Óptica Multiespectral (Landsat 8)
    l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
        .filterBounds(point) \
        .filterDate(date_before, date_after) \
        .median()
        
    # Parámetros de visualización para renderizar los mosaicos
    s1_vis = {'min': -25, 'max': 5}
    l8_vis = {'bands': ['SR_B4', 'SR_B3', 'SR_B2'], 'min': 0, 'max': 30000}
    
    try:
        # Generar los Map IDs (URLs dinámicas temporales para tu mapa en el frontend)
        s1_map = ee.data.getMapId({'image': s1, 'visParams': s1_vis})
        l8_map = ee.data.getMapId({'image': l8, 'visParams': l8_vis})
        
        return {
            "sar_tile_url": s1_map['tile_fetcher'].url_format,
            "optical_tile_url": l8_map['tile_fetcher'].url_format
        }
    except Exception as e:
        return {"error": str(e)}