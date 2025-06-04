import sys
import os

# Voeg project root toe aan sys.path zodat 'routes' en 'domain' gevonden worden
topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, topdir)

import pytest
from fastapi import FastAPI
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
        # Stel vooraf notify_report_done op True, zodat de loop in configuration direct stopt
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
            return {"result": ["cfg1", "cfg2"]}
        if action == "GetBaseReport":
            return {"result": {"status": "Accepted"}}
        if action == "GetVariables":
            return {
                "result": {
                    "get_variable_result": [
                        {
                            "variable": {"name": entry["variable"]["name"]},
                            "attributeValue": "val",
                            "attributeStatus": "Accepted"
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
    # Registreer twee sessies: één OCPP 1.6 en één OCPP 2.0.1
    v16 = FakeSession("cp16", OCPPVersion.V16)
    v201 = FakeSession("cp201", OCPPVersion.V201)
    registry._items["cp16"] = v16
    registry._items["cp201"] = v201
    return

# -------------------------- TESTS -------------------------------

def test_set_and_get_alias(client, registry):
    # 1) Set alias via PUT
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

def test_enable_disable(client):
    # Begin‐status: inactive
    response = client.get("/charge-points/cp16/settings")
    assert response.json()["active"] is False

    # Enable endpoint
    response = client.post("/charge-points/cp16/enable")
    assert response.status_code == 200
    assert response.json() == {"id": "cp16", "active": True}

    # Disable endpoint
    response = client.post("/charge-points/cp16/disable")
    assert response.status_code == 200
    assert response.json() == {"id": "cp16", "active": False}

def test_send_generic_command(client, command_service):
    payload = {"action": "TestAction", "parameters": {"foo": "bar"}}
    response = client.post("/charge-points/cp16/commands", json=payload)
    assert response.status_code == 200
    # De response‐structuur bevat een “result” met status OK
    assert response.json()["result"]["status"] == "OK"

    # Controleer dat FakeCommandService de call heeft geregistreerd
    sent = command_service.sent_commands[-1]
    assert sent["cp_id"] == "cp16"
    assert sent["action"] == "TestAction"
    assert sent["parameters"] == {"foo": "bar"}

def test_remote_start_v16_and_v201(client, command_service):
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

def test_remote_stop_v16_and_v201(client, command_service):
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

def test_set_current_v16_and_v201(client, command_service):
    # --- OCPP 1.6
    response = client.post("/charge-points/cp16/charging-current", json=1)
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "ChangeConfiguration"
    assert sent["parameters"] == {"key": "MaxChargingCurrent", "value": "1"}

    # --- OCPP 2.0.1
    response = client.post("/charge-points/cp201/charging-current", json=5)
    sent = command_service.sent_commands[-1]
    assert sent["action"] == "SetVariables"
    # Controleer dat de structuur klopt
    key_struct = sent["parameters"]["key"]
    assert key_struct["component"]["name"] == "SmartChargingCtrlr"
    assert key_struct["variable_name"] == "ChargingCurrent"
    assert sent["parameters"]["value"] == "5"

def test_configuration_v16_and_v201(client, command_service):
    # --- OCPP 1.6: laat opname van GetConfiguration‐shift zien
    response = client.get("/charge-points/cp16/configuration")
    assert response.status_code == 200
    assert response.json() == {"result": ["cfg1", "cfg2"]}

    # --- OCPP 2.0.1: FakeSession heeft notify_report_done=True en latest_config=[]
    response = client.get("/charge-points/cp201/configuration")
    assert response.status_code == 200
    data = response.json()
    # Status moet “Accepted” zijn (uit onze FakeCommandService)
    assert data["status"] == "Accepted"
    # configuration_key is een lijst (kan leeg zijn, want FakeSession.latest_config was leeg)
    assert isinstance(data["configuration_key"], list)

def test_list_cps(client, registry):
    # Twee sessies “cp16” en “cp201” stonden geregistreerd in de fixture
    response = client.get("/get-all-charge-points")
    assert response.status_code == 200
    connected = response.json()["connected"]
    ids = {item["id"] for item in connected}
    assert "cp16" in ids and "cp201" in ids
