"""
Módulo Máquina del Tiempo Multi-Espectral y Criosférica (NASA GIBS / Worldview WMTS).
Genera URLs de mosaicos {z}/{y}/{x} listos para Leaflet, Mapbox o Deck.gl
sin necesidad de llaves ni descargas pesadas, junto con el bloque satellites_metadata.
"""

GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

TIMEMACHINE_CATALOG = {
    "incendios": {
        "nombre": "Incendios Forestales, Cicatrices de Quema y Apagones",
        "gibs_layer": "VIIRS_NOAA20_CorrectedReflectance_BandsM11-I2-I1",
        "gibs_layer_pre2018": "MODIS_Terra_CorrectedReflectance_Bands721",
        "gibs_base_layer": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
        "gibs_base_layer_pre2018": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "jpg",
        "bbox_delta_deg": 0.6,
        "recommended_zoom": 9,
        "satellites_metadata": [
            {
                "mision": "GOES-16 / GOES-18",
                "agencia": "NOAA / NASA",
                "sensor": "ABI (Advanced Baseline Imager) & GLM (Geostationary Lightning Mapper)",
                "resolucion_espacial": "500 m – 2 km",
                "tiempo_revisita": "5 a 15 minutos",
                "bandas": "Infrarrojo de Onda Corta (3.9 µm) y Óptico de Rayos (777.4 nm)",
                "medicion_cientifica": "Detección ultra-rápida de ignición térmica, evolución de frentes de fuego y destellos de rayos."
            },
            {
                "mision": "NOAA-20 / NOAA-21",
                "agencia": "NASA / NOAA",
                "sensor": "VIIRS (Bandas I1-I5 y Day/Night Band DNB)",
                "resolucion_espacial": "375 m (Focos activos) / 750 m (DNB Luz Nocturna)",
                "tiempo_revisita": "12 horas",
                "bandas": "SWIR/MIR (I4 3.74 µm, M11 2.25 µm) y Visible/NIR DNB (0.5–0.9 µm)",
                "medicion_cientifica": "Focos térmicos de alta precisión a 375 m, Potencia Radiativa del Fuego (FRP) y monitoreo de luz nocturna DNB para detectar apagones por desastre."
            },
            {
                "mision": "Sentinel-2 (A/B/C)",
                "agencia": "ESA Copernicus",
                "sensor": "MSI (MultiSpectral Instrument)",
                "resolucion_espacial": "10 m – 20 m",
                "tiempo_revisita": "5 días",
                "bandas": "NIR (B8A: 865 nm) y SWIR (B12: 2190 nm)",
                "medicion_cientifica": "Severidad de quema mediante el índice NBR (Normalized Burn Ratio) en bandas SWIR a 20 m."
            }
        ]
    },
    "inundaciones_sismos": {
        "nombre": "Inundaciones, Deslaves y Deformación Sísmica (SAR + Precipitación)",
        "gibs_layer": "MODIS_Terra_CorrectedReflectance_Bands721",
        "gibs_layer_pre2018": "MODIS_Terra_CorrectedReflectance_Bands721",
        "gibs_base_layer": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
        "gibs_base_layer_pre2018": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "jpg",
        "bbox_delta_deg": 0.6,
        "recommended_zoom": 9,
        "satellites_metadata": [
            {
                "mision": "Sentinel-1 (A/C)",
                "agencia": "ESA Copernicus",
                "sensor": "C-SAR (Radar de Apertura Sintética en Banda C)",
                "resolucion_espacial": "5 x 20 m (Modo IW)",
                "tiempo_revisita": "6 a 12 días",
                "bandas": "Banda C (5.405 GHz / 5.6 cm) con doble polarización VV/VH",
                "medicion_cientifica": "Detección de lámina de agua bajo nubes y de noche (baja retrodispersión especular) e interferometría diferencial (InSAR) milimétrica para fallas sísmicas."
            },
            {
                "mision": "GPM (Global Precipitation Measurement)",
                "agencia": "NASA / JAXA",
                "sensor": "IMERG (Integrated Multi-satellitE Retrievals for GPM)",
                "resolucion_espacial": "10 km (0.1° x 0.1°)",
                "tiempo_revisita": "30 minutos",
                "bandas": "Microondas pasivas (10–183 GHz) + Radar de Precipitación de Doble Frecuencia (Ku/Ka)",
                "medicion_cientifica": "Tasa de precipitación acumulada en mm/hora cada 30 min para modelado hidrológico de inundaciones y alerta de deslaves."
            }
        ]
    },
    "agricultura_sequia": {
        "nombre": "Agricultura de Precisión, Sequía y Humedad de Suelo",
        "gibs_layer": "MODIS_Terra_NDVI_8Day",
        "gibs_layer_pre2018": "MODIS_Terra_NDVI_8Day",
        "gibs_base_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "gibs_base_layer_pre2018": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "png",
        "bbox_delta_deg": 1.0,
        "recommended_zoom": 8,
        "satellites_metadata": [
            {
                "mision": "Sentinel-2 (A/B/C)",
                "agencia": "ESA Copernicus",
                "sensor": "MSI (MultiSpectral Instrument)",
                "resolucion_espacial": "10 m – 20 m",
                "tiempo_revisita": "5 días",
                "bandas": "Rojo (B4), Red-Edge (B5), NIR (B8) y SWIR (B11)",
                "medicion_cientifica": "Índices de vigor vegetal (NDVI), contenido de clorofila en borde rojo (NDRE) y estrés hídrico del dosel (NDMI) a 10–20 m."
            },
            {
                "mision": "SMAP (Soil Moisture Active Passive)",
                "agencia": "NASA",
                "sensor": "Radiómetro de Microondas en Banda L",
                "resolucion_espacial": "9 km – 36 km",
                "tiempo_revisita": "2 a 3 días",
                "bandas": "Banda L (1.41 GHz)",
                "medicion_cientifica": "Humedad superficial volumétrica (m³/m³) en los primeros 5 cm del suelo y estado de congelación/deshielo."
            }
        ]
    },
    "atmosfera_volcanes": {
        "nombre": "Gases Traza, Plumas Volcánicas y Contaminación Atmosférica",
        "gibs_layer": "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
        "gibs_layer_pre2018": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "gibs_base_layer": "MODIS_Combined_Value_Added_AOD",
        "gibs_base_layer_pre2018": "MODIS_Combined_Value_Added_AOD",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "jpg",
        "bbox_delta_deg": 1.2,
        "recommended_zoom": 7,
        "satellites_metadata": [
            {
                "mision": "Sentinel-5P",
                "agencia": "ESA Copernicus",
                "sensor": "TROPOMI (TROPOspheric Monitoring Instrument)",
                "resolucion_espacial": "3.5 x 5.5 km",
                "tiempo_revisita": "Diario (Cobertura global cada 24 horas)",
                "bandas": "Ultravioleta (UV), Visible (VIS), Infrarrojo Cercano (NIR) e Infrarrojo de Onda Corta (SWIR)",
                "medicion_cientifica": "Espectrometría diaria de gases traza en columna atmosférica: Monóxido de Carbono (CO por incendios), Dióxido de Azufre (SO2 por erupciones volcánicas), Dióxido de Nitrógeno (NO2) y Metano (CH4)."
            }
        ]
    },
    "historico_50_anos": {
        "nombre": "Archivo Histórico de 50 Años, Glaciares, Bosques y Topografía",
        "gibs_layer": "MODIS_Terra_CorrectedReflectance_Bands367",
        "gibs_layer_pre2018": "MODIS_Terra_CorrectedReflectance_Bands367",
        "gibs_base_layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "gibs_base_layer_pre2018": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "tile_matrix_set": "GoogleMapsCompatible_Level9",
        "format": "jpg",
        "bbox_delta_deg": 0.8,
        "recommended_zoom": 8,
        "satellites_metadata": [
            {
                "mision": "Landsat 1–9 (Archivo continuo desde 1972: Landsat 8/9 actual)",
                "agencia": "NASA / USGS",
                "sensor": "OLI-2 (Operational Land Imager) & TIRS-2 (Thermal Infrared Sensor)",
                "resolucion_espacial": "30 m (Multiespectral / Térmico re-muestreado) / 15 m (Pancromático)",
                "tiempo_revisita": "8 días (combinando Landsat 8 y 9)",
                "bandas": "Visible, NIR, SWIR 1/2 y Bandas Térmicas 10/11 (10.6–12.5 µm)",
                "medicion_cientifica": "Cambio multitemporal de uso de suelo, retroceso glaciar, deforestación y Temperatura Superficial Terrestre (LST / Islas de Calor) a 30 m."
            },
            {
                "mision": "ALOS PALSAR & SRTM (Shuttle Radar Topography Mission)",
                "agencia": "JAXA / NASA / ASF",
                "sensor": "PALSAR (SAR Banda L) e Interferómetro Radar SRTM",
                "resolucion_espacial": "12.5 m (ALOS PALSAR Radiometric Terrain Corrected) y 30 m (SRTM DEM)",
                "tiempo_revisita": "Cobertura base topográfica y ciclos de 14–46 días (ALOS)",
                "bandas": "Banda L (1.27 GHz / 23.6 cm, polarización HH/HV) y Banda C/X (SRTM)",
                "medicion_cientifica": "Modelos Digitales de Elevación (DEM) de alta precisión para escorrentías/inundaciones y estimación de estructura/biomasa forestal en Banda L."
            }
        ]
    }
}

# Alias de compatibilidad
TIMEMACHINE_CATALOG["historico_glaciares_bosques"] = TIMEMACHINE_CATALOG["historico_50_anos"]


def _is_pre_2018(date_str: str) -> bool:
    try:
        year = int(str(date_str).strip()[:4])
        return year < 2018
    except Exception:
        return False


def _select_layer(config: dict, date_str: str, is_base: bool = False) -> str:
    if is_base:
        layer = config["gibs_base_layer_pre2018"] if _is_pre_2018(date_str) else config["gibs_base_layer"]
    else:
        layer = config["gibs_layer_pre2018"] if _is_pre_2018(date_str) else config["gibs_layer"]

    # Garantizar que si por cualquier razón una capa VIIRS_ se pide antes de 2018, use MODIS_Terra_
    if _is_pre_2018(date_str) and layer.startswith("VIIRS_"):
        if "BandsM11" in layer:
            return "MODIS_Terra_CorrectedReflectance_Bands721"
        return "MODIS_Terra_CorrectedReflectance_TrueColor"
    return layer


def _build_gibs_url(layer: str, date_str: str, matrix_set: str, ext: str) -> str:
    return f"{GIBS_BASE}/{layer}/default/{date_str}/{matrix_set}/{{z}}/{{y}}/{{x}}.{ext}"


def get_timemachine_layers(
    lat: float = 24.0277,
    lon: float = -104.6531,
    before_date: str = "2020-05-15",
    after_date: str = "2026-11-10",
    mode: str = "incendios"
) -> dict:
    """
    Devuelve las URLs de mosaicos NASA GIBS / Worldview WMTS ({z}/{y}/{x}) para before_date y after_date
    (usando VIIRS_NOAA20_ para 2018–2026 y MODIS_Terra_ para fechas previas a 2018),
    el bloque satellites_metadata de misiones activas y el bounding_box para centrar la cámara del mapa.
    """
    mode_key = mode.strip().lower()
    config = TIMEMACHINE_CATALOG.get(mode_key, TIMEMACHINE_CATALOG["incendios"])
    canonical_mode = mode_key if mode_key in TIMEMACHINE_CATALOG else "incendios"

    delta = config["bbox_delta_deg"]
    min_lon = round(lon - delta, 5)
    min_lat = round(lat - delta, 5)
    max_lon = round(lon + delta, 5)
    max_lat = round(lat + delta, 5)

    before_layer = _select_layer(config, before_date, is_base=False)
    after_layer = _select_layer(config, after_date, is_base=False)
    before_base_layer = _select_layer(config, before_date, is_base=True)
    after_base_layer = _select_layer(config, after_date, is_base=True)

    matrix_set = config["tile_matrix_set"]
    ext = config["format"]

    before_tile_url = _build_gibs_url(before_layer, before_date, matrix_set, ext)
    after_tile_url = _build_gibs_url(after_layer, after_date, matrix_set, ext)

    before_truecolor_url = _build_gibs_url(before_base_layer, before_date, "GoogleMapsCompatible_Level9", "jpg")
    after_truecolor_url = _build_gibs_url(after_base_layer, after_date, "GoogleMapsCompatible_Level9", "jpg")

    return {
        "mode": canonical_mode,
        "mode_title": config["nombre"],
        "dates": {
            "before_date": before_date,
            "after_date": after_date,
        },
        "before_tile_url": before_tile_url,
        "after_tile_url": after_tile_url,
        "tiles": {
            "before": {
                "date": before_date,
                "layer_id": before_layer,
                "tile_url": before_tile_url,
                "true_color_tile_url": before_truecolor_url,
            },
            "after": {
                "date": after_date,
                "layer_id": after_layer,
                "tile_url": after_tile_url,
                "true_color_tile_url": after_truecolor_url,
            },
        },
        "satellites_metadata": config["satellites_metadata"],
        "ficha_tecnica": config["satellites_metadata"],
        "bounding_box": {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "leaflet_bounds": [[min_lat, min_lon], [max_lat, max_lon]],
            "center": {"lat": lat, "lon": lon},
            "recommended_zoom": config["recommended_zoom"],
        },
        "available_modes": [
            "incendios",
            "inundaciones_sismos",
            "agricultura_sequia",
            "atmosfera_volcanes",
            "historico_50_anos"
        ],
    }
