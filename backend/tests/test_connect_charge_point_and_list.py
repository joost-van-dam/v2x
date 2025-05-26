# backend/tests/test_connect_charge_point_and_list.py

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Zorg dat `main.py` als module gevonden wordt
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + os.sep + ".."))

from main import app

@pytest.fixture(scope="module")
def client():
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
        # Stuur BootNotification-call
        ws.send_json([
            2,                         # CALL
            "boot-1",                  # call ID
            "BootNotification",        # action
            {"chargePointVendor": "PyTest", "chargePointModel": "Mock"}
        ])

        # Ontvang CALLRESULT
        resp = ws.receive_json()
        assert isinstance(resp, list)
        assert resp[0] == 3          # CALLRESULT
        assert resp[1] == "boot-1"
        assert resp[2]["status"] == "Accepted"

        # **Nu**, terwijl WS nog open is, staat CP-1 in de registry
        r = client.get("/api/v1/get-all-charge-points")
        assert r.status_code == 200
        data = r.json()["connected"]
        assert len(data) == 1
        cp = data[0]
        assert cp["id"] == "CP-1"
        assert cp["ocpp_version"] == "1.6"
        assert cp["active"] is False

    # Na het sluiten van de WS is de sessie uit de registry verwijderd
    r = client.get("/api/v1/get-all-charge-points")
    assert r.status_code == 200
    assert r.json() == {"connected": []}
