import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
import json

# Importeer router en bus uit jouw code
from routes.frontend_ws_routes import router
import application.event_bus as event_bus_module


# ─── DummyRegistry voor WebSocket connect/disconnect ──────────────────────
class DummyRegistry:
    def __init__(self):
        self.registered = []
        self.deregistered = []
        self._all = []

    async def register(self, ws: WebSocket):
        # Voeg ws toe aan actieve lijst
        self.registered.append(ws)
        self._all.append(ws)

    async def deregister(self, ws: WebSocket):
        self.deregistered.append(ws)
        if ws in self._all:
            self._all.remove(ws)

    async def get_all(self):
        # Geef een kopie terug van de actieve websockets
        return list(self._all)


@pytest.mark.asyncio
async def test_websocket_register_and_deregister():
    """
    Test dat wanneer een client een WebSocket op /frontend opent,
    registry.register(...) wordt aangeroepen, en bij sluiting registry.deregister(...).
    """
    registry = DummyRegistry()
    app = FastAPI()
    app.include_router(router(registry))

    # Open WebSocket via TestClient; zodra 'with' instapt, wordt .register aangeroepen
    with TestClient(app).websocket_connect("/frontend") as websocket:
        # registry.register is exact één keer aangeroepen
        assert len(registry.registered) == 1
        # Controleer dat het object in registered overeenkomt met deze websocket
        assert registry.registered[0] is not None

    # Na het sluiten van de context is de WebSocket gesloten → registry.deregister geroepen
    assert len(registry.deregistered) == 1
    # Deregister argument is exact dezelfde websocket
    assert registry.deregistered[0] is registry.registered[0]


def test_broadcast_and_event_subscription(monkeypatch):
    """
    Test de broadcasting-logica via de eventbus-subscriptions:
    - Vervang bus.subscribe zodat we kunnen nagaan welke handlers geregistreerd zijn.
    - Roep een handler aan en verifieer dat alle actieve WS-clients het bericht ontvangen,
      en dat mislukte send_text() leidt tot deregistratie.
    """
    registry = DummyRegistry()

    # Leg vast welke handlers voor welk event worden geregistreerd
    subscribed = {}

    def fake_subscribe(event_name, handler):
        subscribed[event_name] = handler

    # Mook de bus.subscribe methode
    monkeypatch.setattr(event_bus_module.bus, "subscribe", fake_subscribe)

    # Initialiseer de router (hierdoor wordt fake_subscribe aangeroepen voor alle events)
    _ = router(registry)

    # Controleer dat er ten minste voor "MeterValues" een handler is opgeslagen
    assert "MeterValues" in subscribed

    # ─── Maak twee fake WS-objecten ──────────────────────────────────────
    class FakeWS:
        def __init__(self):
            self.sent = []

        async def send_text(self, text: str):
            self.sent.append(text)

    class BadWS:
        def __init__(self):
            self.sent = []

        async def send_text(self, text: str):
            # Simuleer een fout tijdens verzenden
            raise Exception("send failed")

    ws_good = FakeWS()
    ws_bad = BadWS()

    # Vul registry._all met beide WS-instanties
    registry._all = [ws_good, ws_bad]

    # Haal de handler voor "MeterValues" uit onze subscribed-dict
    handler = subscribed["MeterValues"]

    # Roep de handler aan (simuleer een event met extra payload)
    payload = {"foo": "bar", "baz": 123}
    import asyncio

    # Omdat handler een coroutine is, voeren we hem uit via de event loop
    asyncio.get_event_loop().run_until_complete(handler(**payload))

    # ─── Controleer resultaat voor ws_good ───────────────────────────
    # ws_good heeft één JSON-bericht ontvangen
    assert len(ws_good.sent) == 1
    msg = json.loads(ws_good.sent[0])
    # De inhoud moet de “event” bevatten en de extra hoekgegevens
    assert msg["event"] == "MeterValues"
    assert msg["foo"] == "bar"
    assert msg["baz"] == 123

    # ─── Controleer dat ws_bad is verwijderd uit registry._all ────────
    assert ws_bad not in registry._all
    # En dat ws_bad in deregistered staat
    assert ws_bad in registry.deregistered
