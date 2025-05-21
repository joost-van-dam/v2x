# infrastructure/fastapi_websocket_adapter.py
from __future__ import annotations

from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState


class FastAPIWebSocketAdapter:
    """Geeft een FastAPI-WebSocket het interface (`recv`/`send`) dat
    de *ocpp*-bibliotheek verwacht.

    We voorkomen een **double-close**: als Starlette de socket al heeft
    afgesloten mogen we niet nóg eens `websocket.close` sturen, anders
    ontstaat:

        RuntimeError: Unexpected ASGI message 'websocket.close' …

    Daarom controleren we eerst de actuele socket-status.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    # ----------------------------------------------------------- public I/O
    async def recv(self) -> str:
        """Blokkeert tot er tekst binnenkomt."""
        return await self._ws.receive_text()

    async def send(self, message: str) -> None:
        """Stuurt raw-tekst naar de client."""
        await self._ws.send_text(message)

    async def close(self, code: int | None = None) -> None:  # pragma: no cover
        """
        Sluit de WebSocket veilig af.

        • Alleen wanneer de socket nog niet door Starlette is gesloten
        • Negeert RuntimeError’s die bij race-conditions kunnen optreden
        """
        closed_state = getattr(WebSocketState, "CLOSED", WebSocketState.DISCONNECTED)

        if self._ws.application_state not in (closed_state, WebSocketState.DISCONNECTED):
            try:
                await self._ws.close(code or 1000)
            except RuntimeError:
                # Socket was al dicht; negeren
                pass

    # ------------------------------------------------------ convenience prop
    @property
    def client(self) -> Any:  # ip/port tuple
        return self._ws.client
