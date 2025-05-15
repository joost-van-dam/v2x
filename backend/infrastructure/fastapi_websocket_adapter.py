from typing import Any
from fastapi import WebSocket


class FastAPIWebSocketAdapter:
    """
    Adapter die een FastAPI-WebSocket hetzelfde interface geeft als wat
    de OCPP-bibliotheek verwacht (`recv()` / `send()` i.p.v. `receive_text()`).
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    # ------------------------------------------------------------------ pub
    async def recv(self) -> str:
        return await self._ws.receive_text()

    async def send(self, message: str) -> None:
        await self._ws.send_text(message)

    async def close(self, code: int | None = None) -> None:  # pragma: no cover
        await self._ws.close(code or 1000)

    # ------------------------------------------------- convenience props
    @property
    def client(self) -> Any:  # ip/port tuple
        return self._ws.client
