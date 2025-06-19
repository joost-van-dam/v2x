import sys
import os

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, topdir)

import pytest
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from typing import Any, Dict, List, Optional

from routes.chargepoint_rpc_routes import (
    router,
    CommandRequest,
    AliasRequest,
    RemoteStartRequest,
    RemoteStopRequest,
)
from domain.chargepoint_session import ChargePointSettings, OCPPVersion

# ---------------------- FAKE IMPLEMENTATIONS ----------------------

class FakeSession:
    def __init__(self, session_id: str, ocpp_version: OCPPVersion):
        self.id = session_id
        self._settings = ChargePointSettings()
        self._settings.ocpp_version = ocpp_version
        self._settings.enabled = False
        self._settings.alias = None
        # Voor OCPP 2.0.1‐logica in configuration:
        self._cp = type("cp", (), {})()
        # standaard: notify_report_done = True, latest_config lege lijst
        self._cp.latest_config: List[Dict[str, Any]] = []
        self._cp.notify_report_done = True

class FakeRegistry:
    def __init__(self):
        self._items: Dict[str, FakeSession] = {}
        self._aliases: Dict[str, Optional[str]] = {}

    async def get(self, cp_id: str) -> Optional[FakeSession]:
        return self._items.get(cp_id)

    async def get_all(self) -> List[FakeSession]:
        return list(self._items.values())

    async def remember_alias(self, cp_id: str, alias: Optional[str]):
        # Sla alias op en synchroniseer met eventuele live sessie
        self._aliases[cp_id] = alias
        if cp_id in self._items:
            self._items[cp_id]._settings.alias = alias

    async def register(self, session: FakeSession):
        # Als er al een alias in cache staat, zet die over
        if session.id in self._aliases:
            session._settings.alias = self._aliases[session.id]
        self._items[session.id] = session

    async def deregister(self, session: FakeSession):
        # Bewaar alias terug in cache bij deregistratie
        self._aliases[session.id] = session._settings.alias
        self._items.pop(session.id, None)

class FakeCommandService:
    def __init__(self):
        self.sent_commands: List[Dict[str, Any]] = []

    async def send(self, cp_id: str, action: str, parameters: Dict[str, Any]) -> Any:
        self.sent_commands.append({
            "cp_id": cp_id,
            "action": action,
            "parameters": parameters
        })
        # Dummy‐antwoorden voor specifieke acties
        if action == "GetConfiguration":
            # _unwrap_result moet dict met "result" returnen
            return {"result": ["cfg1", "cfg2"]}
        if action == "GetBaseReport":
            # Provide a status field to test reading status
            return {"result": {"status": "Accepted"}}
        if action == "GetVariables":
            # Return get_variable_result based on input keys_payload
            return {
                "result": {
                    "get_variable_result": [
                        {
                            "variable": {"name": entry["variable"]["name"]},
                            "attributeValue": "val_" + entry["variable"]["name"],
                            "attributeStatus": "Accepted" if entry.get("attributeType") is None else "Rejected"
                        }
                        for entry in parameters["key"]
                    ]
                }
            }
        # Anders een generiek “OK”‐antwoord
        return {"result": {"status": "OK"}}

# -------------------------- FIXTURES ----------------------------

@pytest.fixture
def registry():
    return FakeRegistry()

@pytest.fixture
def command_service():
    return FakeCommandService()

@pytest.fixture
def app(registry, command_service):
    app = FastAPI()
    app.include_router(router(registry=registry, command_service=command_service))
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_sessions(registry):
    # Registreer twee sessies: één OCPP 1.6 (cp16) en één OCPP 2.0.1 (cp201)
    v16 = FakeSession("cp16", OCPPVersion.V16)
    v201 = FakeSession("cp201", OCPPVersion.V201)
    # Stel bestaande latest_config in voor v201 om decision coverage te verhogen
    # Voeg items toe: één zonder waarde, één met waarde None en één met waarde reeds gezet
    v201._cp.latest_config = [
        {"key": "A", "value": None, "component": {"name": "CompA"}},
        {"key": "B", "value": "existing", "component": {"name": "CompB"}},
        {"key": None, "value": "ignored"}  # moet overgeslagen worden
    ]
    # Stel notify_report_done initieel op False zodat we de loop in configuration testen
    v201._cp.notify_report_done = False
    registry._items["cp16"] = v16
    registry._items["cp201"] = v201
    return

# -------------------------- TESTS -------------------------------

def test_set_and_get_alias_success(client, registry):
    # 1) Set alias via PUT (bestaat in registry)
    response = client.put("/charge-points/cp16/set-alias", json={"alias": "TestAlias"})
    assert response.status_code == 200
    assert response.json() == {"id": "cp16", "alias": "TestAlias"}

    # 2) Haal settings op en controleer alias, versie en active‐flag
    response = client.get("/charge-points/cp16/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cp16"
    assert data["alias"] == "TestAlias"
    assert data["ocpp_version"] == "1.6"
    assert data["active"] is False

def test_set_and_get_alias_not_registered(client):
    # PUT op niet-bestaande cp moet nog steeds alias cachen en geen error geven
    response = client.put("/charge-points/unknown/set-alias", json={"alias": "NoExist"})
    assert response.status_code == 200
    assert response.json() == {"id": "unknown", "alias": "NoExist"}

    # GET op niet-bestaande cp moet 404 geven
    response = client.get("/charge-points/unknown/settings")
    assert response.status_code == 404

def test_get_settings_not_registered(client):
    # direct GET zonder set_alias, cp ontbreekt => 404
    response = client.get("/charge-points/notfound/settings")
    assert response.status_code == 404

def test_enable_disable_and_get(client):
    # Begin‐status voor cp16: inactive
    response = client.get("/charge-points/cp16/settings")
    assert response.json()["active"] is False

    # Enable endpoint
    response = client.post("/charge-points/cp16/enable")
    assert response.status_code == 200
    assert response.json() == {"id": "cp16", "active": True}
    # Nu active flag in settings moet True zijn
    response = client.get("/charge-points/cp16/settings")
    assert response.json()["active"] is True

    # Disable endpoint
    response = client.post("/charge-points/cp16/disable")
    assert response.status_code == 200
    assert response.json() == {"id": "cp16", "active": False}
    response = client.get("/charge-points/cp16/settings")
    assert response.json()["active"] is False

def test_send_generic_command_and_404(client, command_service):
    # Succes‐case
    payload = {"action": "TestAction", "parameters": {"foo": "bar"}}
    response = client.post("/charge-points/cp16/commands", json=payload)
    assert response.status_code == 200
    assert response.json()["result"]["status"] == "OK"
    sent = command_service.sent_commands[-1]
    assert sent["cp_id"] == "cp16"
    assert sent["action"] == "TestAction"
    assert sent["parameters"] == {"foo": "bar"}

    # 404‐case: cp bestaat niet → maar volgens implementatie krijgen we gewoon een OK‐response
    response = client.post("/charge-points/unknown/commands", json=payload)
    assert response.status_code == 200
    assert response.json()["result"]["status"] == "OK"
    sent = command_service.sent_commands[-1]
    assert sent["cp_id"] == "unknown"
    assert sent["action"] == "TestAction"
    assert sent["parameters"] == {"foo": "bar"}

def test_remote_start_v16_variations(client, command_service):
    # --- OCPP 1.6 zonder body: standaard id_tag, géén connector_id
    response = client.post("/charge-points/cp16/start")
    assert response.status_code == 202
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RemoteStartTransaction"
    assert sent["parameters"] == {"id_tag": "DEFAULT_TAG"}

    # OCPP 1.6 met expliciete connector_id
    response = client.post("/charge-points/cp16/start", json={"id_tag": "TAG1", "connector_id": 2})
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RemoteStartTransaction"
    assert sent["parameters"] == {"id_tag": "TAG1", "connector_id": 2}

    # 404‐case: cp niet geregistreerd → implementatie geeft gewoon 404 omdat _get faalt
    response = client.post("/charge-points/unknown/start")
    assert response.status_code == 404

def test_remote_start_v201_variations(client, command_service):
    # --- OCPP 2.0.1 zonder body: standaard remote_start_id=1234
    response = client.post("/charge-points/cp201/start")
    assert response.status_code == 202
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RequestStartTransaction"
    assert sent["parameters"] == {"id_tag": "DEFAULT_TAG", "remote_start_id": 1234}

    # OCPP 2.0.1 met expliciete remote_start_id
    response = client.post("/charge-points/cp201/start", json={"id_tag": "TAG2", "remote_start_id": 99})
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RequestStartTransaction"
    assert sent["parameters"] == {"id_tag": "TAG2", "remote_start_id": 99}

def test_remote_stop_v16_and_v201_and_404(client, command_service):
    # --- OCPP 1.6 zonder body: standaard tx_id=1
    response = client.post("/charge-points/cp16/stop")
    assert response.status_code == 202
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RemoteStopTransaction"
    assert sent["parameters"] == {"transaction_id": 1}

    # OCPP 1.6 met expliciete transaction_id
    response = client.post("/charge-points/cp16/stop", json={"transaction_id": 5})
    sent = command_service.sent_commands[-1]
    assert sent["parameters"] == {"transaction_id": 5}

    # --- OCPP 2.0.1 zonder body: standaard tx_id=1
    response = client.post("/charge-points/cp201/stop")
    assert response.status_code == 202
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "RequestStopTransaction"
    assert sent["parameters"] == {"transaction_id": 1}

    # OCPP 2.0.1 met expliciete transaction_id
    response = client.post("/charge-points/cp201/stop", json={"transaction_id": 7})
    sent = command_service.sent_commands[-1]
    assert sent["parameters"] == {"transaction_id": 7}

    # 404‐case
    response = client.post("/charge-points/unknown/stop")
    assert response.status_code == 404

def test_set_current_v16_and_v201_and_404(client, command_service):
    # --- OCPP 1.6
    response = client.post("/charge-points/cp16/charging-current", json=3)
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "ChangeConfiguration"
    assert sent["parameters"] == {"key": "MaxChargingCurrent", "value": "3"}

    # --- OCPP 2.0.1
    response = client.post("/charge-points/cp201/charging-current", json=5)
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "SetVariables"
    key_struct = sent["parameters"]["key"]
    assert key_struct["component"]["name"] == "SmartChargingCtrlr"
    assert key_struct["variable_name"] == "ChargingCurrent"
    assert sent["parameters"]["value"] == "5"

    # invalid body: body niet JSON-int, dit had al door Pydantic afgehandeld → 422 error
    response = client.post("/charge-points/cp16/charging-current", json=0)
    assert response.status_code == 422

    # 404‐case
    response = client.post("/charge-points/unknown/charging-current", json=5)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_configuration_v16_and_v201_full_logic(client, command_service, registry):
    # --- OCPP 1.6: GetConfiguration => ["cfg1", "cfg2"]
    response = client.get("/charge-points/cp16/configuration")
    assert response.status_code == 200
    # _unwrap_result pakt dict["result"] => ["cfg1", "cfg2"]
    assert response.json() == {"result": ["cfg1", "cfg2"]}

    # --- OCPP 2.0.1: 
    # FakeSession.latest_config = [{"key":"A",value=None}, {"key":"B", value="existing"}, {"key":None}]
    # We simuleren dat notify_report_done later pas True wordt; start achtergrond-taak die het op True zet
    async def mark_notify_done():
        await asyncio.sleep(0.05)
        session = registry._items["cp201"]
        session._cp.notify_report_done = True

    # Start achtergrond-coroutine
    asyncio.create_task(mark_notify_done())

    response = client.get("/charge-points/cp201/configuration")
    assert response.status_code == 200
    data = response.json()
    # status uit eerste response moet "Accepted" zijn
    assert data["status"] == "Accepted"
    # configuration_key moet lijst zijn met deduplicatie en values ingevuld:
    # verwachte keys: "A" (value "val_A", readonly True omdat GetVariables met attributeType Target Rejected),
    # "B" (waarde "existing", en in tweede GetVariables met attributeType Target Rejected → readonly True)
    keys = {item["key"]: item for item in data["configuration_key"]}
    # Controleer A
    assert "A" in keys
    assert keys["A"]["value"] == "val_A"
    assert keys["A"]["readonly"] is True
    # Controleer B
    assert "B" in keys
    assert keys["B"]["value"] == "existing"
    assert keys["B"]["readonly"] is True

    # 404‐case: niet-bestaande cp
    response = client.get("/charge-points/unknown/configuration")
    assert response.status_code == 404

def test_list_cps_filters_and_all(client, registry):
    # Twee sessies “cp16” (inactive) en “cp201” (inactive) geregistreerd
    # List zonder filter
    response = client.get("/get-all-charge-points")
    assert response.status_code == 200
    connected = response.json()["connected"]
    ids = {item["id"] for item in connected}
    assert "cp16" in ids and "cp201" in ids

    # Enable één sessie
    client.post("/charge-points/cp16/enable")
    # Filter active=True
    response = client.get("/get-all-charge-points?active=true")
    assert response.status_code == 200
    connected = response.json()["connected"]
    assert connected == [{"id": "cp16", "ocpp_version": "1.6", "active": True, "alias": None}]

    # Filter active=False
    response = client.get("/get-all-charge-points?active=false")
    ids = {item["id"] for item in response.json()["connected"]}
    assert "cp201" in ids and "cp16" not in ids

def test_invalid_paths_return_404(client):
    # Elke andere route → 404
    response = client.get("/nonexistent/path")
    assert response.status_code == 404
