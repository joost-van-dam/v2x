# backend/main.py

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Application-layer singletons
from application.connection_registry import ConnectionRegistryChargePoint, ConnectionRegistryFrontend
from application.command_service import CommandService
from services.settings_repository import SettingsRepository  
from services.influxdb_service import InfluxDBService
from config import settings   

repo = SettingsRepository(settings().POSTGRES_DSN)    

# API / transport routes
from routes.chargepoint_ws_routes import router as chargepoint_ws_router
from routes.chargepoint_rpc_routes import router as chargepoint_rpc_router
from routes.frontend_ws_routes import router as frontend_ws_router

logger = logging.getLogger("csms")
logger.setLevel(logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):                                
    # DB-connectie + tabel maken
    await repo.init()
    # alias-cache in registry injecteren vóór de app requests binnenkomen
    aliases = {k: v["alias"] for k, v in (await repo.load_all()).items()}
    cp_registry.preload_aliases(aliases)        # type: ignore[attr-defined]
    yield
    await repo.close()

app = FastAPI(
    title="CSMS API (clean-architecture edition)",
    version="0.2.0",
    description=(
        "Multilayer Charging-Station Management System following SOLID & clean "
        "architecture principles."
    ),
    lifespan=lifespan,     
    contact={
        "name": "Joost van Dam",
        "email": "ja.vandam3@student.avans.nl",
        "url": "https://www.mnext.nl/lectoraat/smart-energy/",
    },
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
cp_registry = ConnectionRegistryChargePoint(repo) 
fe_registry = ConnectionRegistryFrontend()
command_service = CommandService(cp_registry)
InfluxDBService()

# Mount routers
app.include_router(
    chargepoint_ws_router(registry=cp_registry),
    prefix="/api/ws",
    tags=["WebSocket – Charge Point"],
)
app.include_router(
    chargepoint_rpc_router(registry=cp_registry, command_service=command_service),
    prefix="/api/v1",
    tags=["RPC – Charge Point"],
)
app.include_router(
    frontend_ws_router(registry=fe_registry),
    prefix="/api/ws",
    tags=["WebSocket – Front-end"],
)

@app.get("/", tags=["Meta"])
async def root() -> dict[str, str]:
    return {"message": "Welcome to the revamped CSMS API"}
