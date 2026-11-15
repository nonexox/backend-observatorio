from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json

from ingestors import (
    fetch_gdacs_normalized,
    fetch_eonet_normalized,
    fetch_firms_normalized,
    fetch_itslive_normalized
)
from database import upsert_events, get_db_connection, query_disasters
from sar_engine import get_historical_tiles, search_sar_granules
from timemachine import get_timemachine_layers
from predictor import generate_risk_projection

# --- TAREAS EN SEGUNDO PLANO (CRON JOBS) ---
async def sync_fast_events():
    print("Cron: Descargando GDACS, EONET y FIRMS a escala global...")
    gdacs = await fetch_gdacs_normalized()
    eonet = await fetch_eonet_normalized()
    firms = await fetch_firms_normalized()
    upsert_events(gdacs + eonet + firms)

async def sync_slow_events():
    print("Cron: Verificando glaciares en ITS_LIVE...")
    itslive = await fetch_itslive_normalized()
    upsert_events(itslive)

# --- GESTOR DE CICLO DE VIDA DE LA API ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    # GDACS y FIRMS cada 15 minutos
    scheduler.add_job(sync_fast_events, 'interval', minutes=15)
    # ITS_LIVE cada 12 horas
    scheduler.add_job(sync_slow_events, 'interval', hours=12)
    scheduler.start()
    print("Planificador de tareas iniciado.")
    yield
    scheduler.shutdown()
    print("Planificador detenido.")

app = FastAPI(
    title="API Observatorio Tierra - NASA Space Apps",
    description="Motor agregador global y análisis SAR / Óptico",
    lifespan=lifespan
)

# --- CONFIGURACIÓN CORS (PASO 4) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite que el frontend local de tu equipo se conecte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/sync-test")
async def sync_test():
    """Ejecución manual temporal de las descargas (Opcional)."""
    gdacs = await fetch_gdacs_normalized()
    eonet = await fetch_eonet_normalized()
    firms = await fetch_firms_normalized()
    itslive = await fetch_itslive_normalized()
    
    todos_los_eventos = gdacs + eonet + firms + itslive
    insertados = upsert_events(todos_los_eventos)
    
    return {
        "status": "Sincronización exitosa",
        "total_descargados": len(todos_los_eventos),
        "insertados_en_db": insertados
    }

@app.get("/api/v1/disasters")
def get_disasters(
    disaster_type: str | None = None,
    min_severity: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None
):
    """Devuelve un FeatureCollection GeoJSON de los eventos activos (con filtro opcional de radio en km)."""
    return query_disasters(
        disaster_type=disaster_type,
        min_severity=min_severity,
        lat=lat,
        lon=lon,
        radius_km=radius_km
    )

# --- NUEVO ENDPOINT: LA MÁQUINA DEL TIEMPO SAR ---
@app.get("/api/v1/historical-compare")
def historical_compare(
    lat: float = Query(..., description="Latitud del desastre"), 
    lon: float = Query(..., description="Longitud del desastre"), 
    date_before: str = Query(..., description="Fecha inicial ej. 2026-01-01"), 
    date_after: str = Query(..., description="Fecha final ej. 2026-05-01")
):
    """Genera URLs de mosaicos satelitales (Radar y Óptico) para el slider de antes y después."""
    tiles = get_historical_tiles(lat, lon, date_before, date_after)
    return tiles

# --- ENDPOINT: ANÁLISIS MULTI-SATÉLITE SAR (ASF / NASA) ---
@app.get("/api/v1/sar-analysis")
def sar_analysis(
    lat: float = Query(..., description="Latitud del punto de desastre"),
    lon: float = Query(..., description="Longitud del punto de desastre"),
    days_back: int = Query(60, description="Días hacia atrás para buscar escenas SAR"),
    max_results: int = Query(10, description="Máximo de escenas SAR a devolver")
):
    """Busca huellas poligonales e imágenes previas SAR (Sentinel-1, ALOS, NISAR) en el catálogo de ASF."""
    return search_sar_granules(lat=lat, lon=lon, days_back=days_back, max_results=max_results)

# --- ENDPOINT: MÁQUINA DEL TIEMPO MULTI-ESPECTRAL (NASA GIBS WMTS) ---
@app.get("/api/v1/timemachine")
def timemachine(
    lat: float = Query(24.0277, description="Latitud del evento"),
    lon: float = Query(-104.6531, description="Longitud del evento"),
    before_date: str = Query("2020-05-15", description="Fecha Antes (YYYY-MM-DD)"),
    after_date: str = Query("2026-11-10", description="Fecha Después (YYYY-MM-DD)"),
    mode: str = Query(
        "incendios",
        description="Modo científico: incendios, inundaciones_sismos, agricultura_sequia, atmosfera_volcanes, historico_50_anos"
    )
):
    """Devuelve URLs de tiles {z}/{y}/{x} NASA GIBS para slider Antes/Después, satellites_metadata y bounding_box."""
    return get_timemachine_layers(
        lat=lat,
        lon=lon,
        before_date=before_date,
        after_date=after_date,
        mode=mode
    )

# --- ENDPOINT: PREDICCIÓN DE RIESGO Y RECOMENDACIÓN NISAR ---
@app.get("/api/v1/predict-risk")
def predict_risk(
    lat: float = Query(24.0277, description="Latitud del evento"),
    lon: float = Query(-104.6531, description="Longitud del evento"),
    disaster_type: str = Query("Fuego", description="Tipo de desastre (ej. Fuego, Inundación, Sismo, Volcán, Desplazamiento Hielo)"),
    horizon_days: int = Query(30, description="Horizonte de proyección en días (ej. 7, 15, 30, 90)")
):
    """Genera el puntaje de riesgo, curva de evolución (+7 a +90 días), polígonos GeoJSON de expansión y acción NISAR."""
    return generate_risk_projection(
        lat=lat,
        lon=lon,
        disaster_type=disaster_type,
        horizon_days=horizon_days
    )