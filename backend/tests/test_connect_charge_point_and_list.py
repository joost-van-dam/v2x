# backend/tests/test_connect_charge_point_and_list.py

import json
import pytest
from starlette.testclient import TestClient

# Importeren van de FastAPI-app uit het backend-package
from backend.main import app

@pytest.fixture(scope="module")
def client():
    # TestClient draait de app in‐process, dus geen aparte server nodig
    return TestClient(app)

def test_root_and_empty_list(client):
    # Health-check
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Welcome to the revamped CSMS API"}

    # Er zijn nog geen CP's verbonden
    r = client.get("/api/v1/get-all-charge-points")
    assert r.status_code == 200
    assert r.json() == {"connected": []}

def test_charge_point_connect_and_list(client):
    # Open WS-verbinding met subprotocol voor OCPP 1.6
    with client.websocket_connect(
        "/api/ws/ocpp/CP-1",
        subprotocols=["ocpp1.6"]
    ) as ws:
        # Stuur BootNotification-call (JSON-RPC-vorm)
        ws.send_json([
            2,                         # MessageTypeId = CALL
            "boot-1",                  # Unique call ID
            "BootNotification",        # Action
            {
                "chargePointVendor": "PyTest",
                "chargePointModel": "Mock"
            }
        ])

        # Ontvang CALLRESULT
        resp = ws.receive_json()
        # [3, call_id, { … }]
        assert isinstance(resp, list)
        assert resp[0] == 3          # MessageTypeId = CALLRESULT
        assert resp[1] == "boot-1"
        assert resp[2]["status"] == "Accepted"

    # Na WS-close moet registry zijn bijgewerkt
    r = client.get("/api/v1/get-all-charge-points")
    assert r.status_code == 200
    data = r.json()["connected"]

    assert len(data) == 1
    cp = data[0]
    assert cp["id"] == "CP-1"
    assert cp["ocpp_version"] == "1.6"
    assert cp["active"] is False  # standaard enabled=False
