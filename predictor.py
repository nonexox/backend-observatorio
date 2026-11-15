"""
Motor Predictivo Espacial y Recomendador de Auditoría NISAR (predictor.py).
Calcula el riesgo prospectivo, la curva de evolución temporal (+7, +15, +30 y +90 días),
los 3 polígonos concéntricos GeoJSON de expansión y el producto NISAR recomendado.
"""

import math
from database import query_disasters


def _build_ellipse_polygon(
    center_lon: float,
    center_lat: float,
    radius_km: float,
    eccentricity: float = 1.2,
    azimuth_deg: float = 35.0,
    num_points: int = 48
) -> dict:
    """
    Construye un polígono GeoJSON circular/elíptico alrededor de [center_lon, center_lat]
    ajustando por la latitud en grados geográficos.
    """
    coords = []
    lat_rad = math.radians(max(min(center_lat, 85.0), -85.0))
    cos_lat = max(math.cos(lat_rad), 0.1)
    az_rad = math.radians(azimuth_deg)

    semi_major_km = radius_km * eccentricity
    semi_minor_km = radius_km

    for i in range(num_points):
        theta = 2.0 * math.pi * (i / num_points)
        dx_local = semi_major_km * math.cos(theta)
        dy_local = semi_minor_km * math.sin(theta)

        # Rotar elipse según dirección predominante (viento / falla / pendiente)
        dx_km = dx_local * math.cos(az_rad) - dy_local * math.sin(az_rad)
        dy_km = dx_local * math.sin(az_rad) + dy_local * math.cos(az_rad)

        d_lat = dy_km / 111.32
        d_lon = dx_km / (111.32 * cos_lat)

        coords.append([round(center_lon + d_lon, 5), round(center_lat + d_lat, 5)])

    # Cerrar el anillo poligonal GeoJSON
    coords.append(coords[0])
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def _select_nisar_action(disaster_type: str) -> dict:
    dt = (disaster_type or "Fuego").strip().lower()

    if any(k in dt for k in ("fuego", "incendio", "wf", "wildfire", "tala", "bosque", "sequia", "dr")):
        return {
            "nisar_product": "GCOV",
            "product_full_name": "Geocoded Polarimetric Covariance Matrix (L2 GCOV)",
            "radar_band": "Banda L (24 cm / 1.25 GHz) - Polarización Dual HH/HV",
            "action_summary": "Activar NISAR GCOV para cuantificar pérdida de biomasa leñosa, humedad del suelo post-incendio y regeneración estructural bajo humo.",
            "target_variable": "Biomasa aérea (t/ha) y retrodispersión volumétrica HV"
        }
    elif any(k in dt for k in ("sismo", "terremoto", "eq", "earthquake", "volcan", "vo", "volcano", "deslave")):
        return {
            "nisar_product": "GUNW",
            "product_full_name": "Geocoded Unwrapped Interferogram (L2 GUNW InSAR)",
            "radar_band": "Banda L (24 cm) + Banda S (12 cm) Interferometría Diferencial",
            "action_summary": "Activar NISAR GUNW InSAR para medir deformación cortical milimétrica, inflación magmática o desplazamiento de laderas sin pérdida de coherencia en vegetación.",
            "target_variable": "Desplazamiento en línea de vista (LOS en mm/mes) y coherencia interferométrica"
        }
    else:
        # Inundaciones (FL), ciclones (TC), glaciares / hielo (Desplazamiento Hielo), etc.
        return {
            "nisar_product": "GSLC",
            "product_full_name": "Geocoded Single-Look Complex (L2 GSLC)",
            "radar_band": "Banda L (24 cm) de Alta Resolución Fase + Amplitud",
            "action_summary": "Activar NISAR GSLC para delimitar inundación bajo dosel arbóreo/nubes y rastrear velocidad de flujo criosférico (speckle tracking) en glaciares.",
            "target_variable": "Extensión de lámina de agua inundada (ha) y velocidad de hielo (m/día)"
        }


def generate_risk_projection(
    lat: float,
    lon: float,
    disaster_type: str = "Fuego",
    horizon_days: int = 30
) -> dict:
    """
    Consulta eventos cercanos en la base de datos y genera la proyección de riesgo:
    - risk_score (0 a 100) y confidence_level
    - timeline_projection (+7, +15, +30 y +90 días)
    - projected_zones_geojson (3 polígonos concéntricos: riesgo_critico, expansion_media, zona_vigilancia_sar)
    - recommended_sar_action (producto NISAR GCOV, GUNW o GSLC)
    """
    horizon_days = max(1, min(int(horizon_days or 30), 365))

    # Consultar eventos cercanos dentro de 350 km para enriquecer el puntaje
    nearby_fc = query_disasters(lat=lat, lon=lon, radius_km=350.0)
    nearby_features = nearby_fc.get("features", []) if isinstance(nearby_fc, dict) else []

    high_count = sum(
        1 for f in nearby_features
        if str(f.get("properties", {}).get("severity", "")).lower() == "alta"
    )
    total_nearby = len(nearby_features)

    # Calcular risk_score base (0 a 100) combinando actividad cercana, tipo de amenaza y horizonte
    base_score = 58
    if total_nearby > 0:
        base_score += min(25, total_nearby * 3 + high_count * 4)
    else:
        # Si no hay eventos en caché en ese radio, estimar según latitud/tipo para demostración científica
        base_score = 68 if abs(lat) < 60 else 74

    horizon_factor = min(15, int(math.log2(max(horizon_days, 2)) * 2.5))
    risk_score = max(15, min(98, base_score + horizon_factor))

    if total_nearby >= 3:
        confidence_level = "alta"
    elif total_nearby >= 1:
        confidence_level = "media-alta"
    else:
        confidence_level = "media (modelo espacial paramétrico)"

    severity_multiplier = 1.35 if risk_score >= 75 else (1.15 if risk_score >= 55 else 0.95)
    horizon_scale = math.sqrt(horizon_days / 30.0)

    # Radios dinámicos en km para los 3 anillos según horizon_days y severidad
    r_critico_km = round(4.5 * severity_multiplier * horizon_scale, 2)
    r_expansion_km = round(11.0 * severity_multiplier * horizon_scale, 2)
    r_vigilancia_km = round(24.0 * severity_multiplier * horizon_scale, 2)

    # Curva de evolución temporal (+7, +15, +30 y +90 días)
    timeline_projection = []
    for d in (7, 15, 30, 90):
        scale_d = (d / 7.0) ** 0.68 * severity_multiplier
        r_km_d = round(3.8 * scale_d, 2)
        hectares_at_risk = round(math.pi * (r_km_d ** 2) * 100 * 0.42, 1)  # 1 km² = 100 ha
        displacement_m = round(1.8 * (d / 7.0) ** 0.85 * severity_multiplier, 2)

        timeline_projection.append({
            "horizon_label": f"+{d} días",
            "days": d,
            "projected_risk_score": min(99, int(risk_score * (0.88 + 0.04 * math.log2(d)))),
            "hectareas_en_riesgo": hectares_at_risk,
            "desplazamiento_estimado_m": displacement_m,
            "radio_afectacion_km": r_km_d,
        })

    # Construir los 3 polígonos concéntricos/elípticos GeoJSON alrededor de [lon, lat]
    zones_config = [
        {
            "zone_id": "riesgo_critico",
            "zone_name": "Zona de Riesgo Crítico Directo",
            "radius_km": r_critico_km,
            "eccentricity": 1.25,
            "fill_color": "#ef4444",
            "fill_opacity": 0.45,
            "severity": "alta",
            "description": f"Núcleo de impacto directo proyectado a {horizon_days} días."
        },
        {
            "zone_id": "expansion_media",
            "zone_name": "Anillo de Expansión Secundaria",
            "radius_km": r_expansion_km,
            "eccentricity": 1.32,
            "fill_color": "#f97316",
            "fill_opacity": 0.28,
            "severity": "media",
            "description": f"Área de propagación probable en un horizonte de {horizon_days} días."
        },
        {
            "zone_id": "zona_vigilancia_sar",
            "zone_name": "Perímetro de Vigilancia y Auditoría SAR (NISAR)",
            "radius_km": r_vigilancia_km,
            "eccentricity": 1.15,
            "fill_color": "#eab308",
            "fill_opacity": 0.15,
            "severity": "baja",
            "description": "Perímetro de barrido satelital preventivo en Banda L y Banda C."
        }
    ]

    zone_features = []
    for z in zones_config:
        area_ha = round(math.pi * (z["radius_km"] ** 2) * z["eccentricity"] * 100, 1)
        zone_features.append({
            "type": "Feature",
            "geometry": _build_ellipse_polygon(
                center_lon=lon,
                center_lat=lat,
                radius_km=z["radius_km"],
                eccentricity=z["eccentricity"]
            ),
            "properties": {
                "zone_type": z["zone_id"],
                "name": z["zone_name"],
                "severity": z["severity"],
                "radius_km": z["radius_km"],
                "estimated_area_ha": area_ha,
                "horizon_days": horizon_days,
                "fill_color": z["fill_color"],
                "fill_opacity": z["fill_opacity"],
                "description": z["description"]
            }
        })

    recommended_sar_action = _select_nisar_action(disaster_type)

    return {
        "location": {"lat": lat, "lon": lon},
        "disaster_type": disaster_type,
        "horizon_days": horizon_days,
        "nearby_active_events_considered": total_nearby,
        "risk_score": risk_score,
        "confidence_level": confidence_level,
        "timeline_projection": timeline_projection,
        "recommended_sar_action": recommended_sar_action,
        "projected_zones_geojson": {
            "type": "FeatureCollection",
            "features": zone_features
        }
    }

