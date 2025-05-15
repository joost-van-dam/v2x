import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------- Application-layer singletons ----------------
from application.connection_registry import (
    ConnectionRegistryChargePoint,
    ConnectionRegistryFrontend,
)
from application.command_service import CommandService

# ---------------- API / transport routes ----------------
from routes.chargepoint_ws_routes import router as chargepoint_ws_router
from routes.chargepoint_rpc_routes import router as chargepoint_rpc_router
from routes.frontend_ws_routes import router as frontend_ws_router

# ---------------------------------------------------------------------------
# App-bootstrap
# ---------------------------------------------------------------------------
logger = logging.getLogger("csms")
logger.setLevel(logging.INFO)

app = FastAPI(
    title="CSMS API (clean-architecture edition)",
    version="0.2.0",
    description=(
        "Multilayer Charging-Station Management System following SOLID & clean "
        "architecture principles."
    ),
    contact={
        "name": "Joost van Dam",
        "email": "ja.vandam3@student.avans.nl",
        "url": "https://www.mnext.nl/lectoraat/smart-energy/",
    },
)

# ---------------------------------------------------- CORS / middleware ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------ Dependency singletons ----
cp_registry = ConnectionRegistryChargePoint()
fe_registry = ConnectionRegistryFrontend()
command_service = CommandService(cp_registry)

# ------------------------------------------- Mount the route-modules ------
# Routers krijgen de concrete dependencies via partial application
app.include_router(
    chargepoint_ws_router(
        registry=cp_registry,
    ),
    prefix="/api/ws",
    tags=["WebSocket – Charge Point"],
)

app.include_router(
    chargepoint_rpc_router(
        registry=cp_registry,
        command_service=command_service,
    ),
    prefix="/api",
    tags=["RPC – Charge Point"],
)

app.include_router(
    frontend_ws_router(registry=fe_registry),
    prefix="/api/ws",
    tags=["WebSocket – Front-end"],
)

# ------------------------------------------------------------- root ------
@app.get("/", tags=["Meta"])
async def root() -> dict[str, str]:
    return {"message": "Welcome to the revamped CSMS API"}
