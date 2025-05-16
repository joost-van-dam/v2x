from typing import Any
from fastapi import WebSocket
from starlette.websockets import WebSocketState


class FastAPIWebSocketAdapter:
    """Adapter die een FastAPI‑WebSocket het interface geeft dat de
    *ocpp*‑bibliotheek verwacht (`recv()`/`send()`).

    Tegelijk voorkomen we een **double close**: Starlette sluit de socket
    al wanneer de client disconnect.  Proberen wij daarna nogmaals
    `websocket.close` te sturen, dan resulteert dat in:
    *RuntimeError: Unexpected ASGI message 'websocket.close'…*  
    Dit lossen we op door eerst de state te controleren.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    # ------------------------------------------------------------------ public I/O
    async def recv(self) -> str:
        return await self._ws.receive_text()

    async def send(self, message: str) -> None:
        await self._ws.send_text(message)

    async def close(self, code: int | None = None) -> None:  # pragma: no cover
        # Alleen sluiten als Starlette dat nog niet heeft gedaan
        if self._ws.application_state not in (WebSocketState.CLOSED, WebSocketState.DISCONNECTED):
            try:
                await self._ws.close(code or 1000)
            except RuntimeError:
                # Socket was al dicht; negeren
                pass

    # ------------------------------------------------ convenience prop
    @property
    def client(self) -> Any:  # ip/port tuple
        return self._ws.client
