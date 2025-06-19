import json
import threading
import pytest
from fastapi.testclient import TestClient

from application.command_service import CommandService

# ------------------------------------------------------------------------------
# Mock CommandService.send for all tests
# ------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_command_service(monkeypatch):
    """
    Mock alle OCPP-calls zodat start/stop/configuration direct Accepted/empty teruggeven
    zonder echte WebSocket-interactie.
    """
    async def fake_send(self, cp_id: str, action: str, params: dict):
        # Remote start/stop
        if action in {
            "RemoteStartTransaction", "RequestStartTransaction",
            "RemoteStopTransaction",  "RequestStopTransaction"
        }:
            return {"status": "Accepted"}
        # Configuration for OCPP 1.6
        if action == "GetConfiguration":
            return {"configurationKey": []}
        # Fallback: lege dict
        return {}

    monkeypatch.setattr(CommandService, "send", fake_send)


@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def cp4_session(client):
    """
    Simuleert één OCPP 1.6-laadpaal (CP-4). Een achtergrond-thread
    beantwoordt elk OCPP-CALL-bericht van de backend met een geldig
    CALLRESULT. Zo voorkomen we time-outs in de HTTP-eindpunten.
    """
    with client.websocket_connect(
        "/api/ws/ocpp/CP-4",
        subprotocols=["ocpp1.6"],
    ) as ws:
        # ── BootNotification ──────────────────────────────────────────
        ws.send_json(
            [
                2,
                "boot-4",
                "BootNotification",
                {"chargePointVendor": "E2ETest", "chargePointModel": "Mock"},
            ]
        )
        resp = ws.receive_json()
        assert resp[0] == 3  # CALLRESULT

        # ── responder-thread ─────────────────────────────────────────
        def responder() -> None:
            try:
                while True:
                    try:
                        raw = ws.receive_text()
                    except Exception:
                        break  # socket dicht

                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if not isinstance(msg, list) or msg[0] != 2:
                        continue  # niet een CALL

                    call_id = msg[1]
                    action = msg[2]

                    # Minimale correcte payloads
                    if action == "RemoteStartTransaction":
                        payload = {"status": "Accepted"}
                    elif action == "RemoteStopTransaction":
                        payload = {"status": "Accepted"}
                    elif action == "GetConfiguration":
                        payload = {"configurationKey": [], "unknownKey": []}
                    elif action == "ChangeConfiguration":
                        payload = {"status": "Accepted"}
                    else:
                        payload = {"status": "Accepted"}

                    ws.send_text(json.dumps([3, call_id, payload]))
            except Exception:
                pass  # fouten in de responder mogen tests niet breken

        t = threading.Thread(target=responder, daemon=True)
        t.start()
        try:
            yield
        finally:
            try:
                ws.close()
            finally:
                t.join(timeout=1)


# ───────────────────────────────────────────────────────────────
#                              TESTS
# ───────────────────────────────────────────────────────────────
def test_list_before_and_after_connect(client, cp4_session):
    r = client.get("/api/v1/get-all-charge-points")
    assert r.status_code == 200
    assert "CP-4" in [cp["id"] for cp in r.json()["connected"]]

    r = client.get("/api/v1/get-all-charge-points?active=false")
    assert r.status_code == 200
    assert "CP-4" in [cp["id"] for cp in r.json()["connected"]]

    r = client.get("/api/v1/get-all-charge-points?active=true")
    assert r.status_code == 200
    assert r.json()["connected"] == []


def test_set_alias_and_get_settings(client, cp4_session):
    r = client.put(
        "/api/v1/charge-points/CP-4/set-alias",
        json={"alias": "MyChargPoint"},
    )
    assert r.status_code == 200
    assert r.json() == {"id": "CP-4", "alias": "MyChargPoint"}

    r = client.get("/api/v1/charge-points/CP-4/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["alias"] == "MyChargPoint"
    assert data["active"] is False


def test_enable_disable_and_settings(client):
    r = client.post("/api/v1/charge-points/CP-4/enable")
    assert r.status_code == 200
    assert r.json() == {"id": "CP-4", "active": True}

    r = client.get("/api/v1/charge-points/CP-4/settings")
    assert r.status_code == 200
    assert r.json()["active"] is True

    r = client.post("/api/v1/charge-points/CP-4/disable")
    assert r.status_code == 200
    assert r.json() == {"id": "CP-4", "active": False}

    r = client.get("/api/v1/charge-points/CP-4/settings")
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_remote_start_and_stop_via_http(client):
    # Remote start
    r = client.post("/api/v1/charge-points/CP-4/start")
    assert r.status_code == 202
    assert r.json()["status"] == "Accepted"

    # Remote stop
    r = client.post("/api/v1/charge-points/CP-4/stop")
    assert r.status_code == 202
    assert r.json()["status"] == "Accepted"


def test_configuration_via_http(client):
    r = client.get("/api/v1/charge-points/CP-4/configuration")
    assert r.status_code == 200
    data = r.json()
    # responder stuurt lege configurationKey-lijst
    assert data["configurationKey"] == []
