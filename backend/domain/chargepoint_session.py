from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------ #
# Transport-abstracties
# ------------------------------------------------------------------------ #
class WebSocketChannel(Protocol):
    async def recv(self) -> str: ...
    async def send(self, message: str) -> None: ...
    async def close(self, code: int | None = None) -> None: ...


class IOcppEndpoint(Protocol):
    """Interface die zowel CP-v1.6 als CP-v2.0.1 implementeert."""
    id: str

    async def route_message(self, raw: str) -> None: ...
    async def call(self, message: Any) -> Any: ...


# ------------------------------------------------------------------------ #
# OCPP-versies
# ------------------------------------------------------------------------ #
class OCPPVersion(str, Enum):
    V16 = "1.6"
    V201 = "2.0.1"


# ------------------------------------------------------------------------ #
# Instelling-placeholder
# ------------------------------------------------------------------------ #
class ChargePointSettings:
    id: str
    alias: str | None = None
    enabled: bool = False
    ocpp_version: OCPPVersion = OCPPVersion.V16


# ------------------------------------------------------------------------ #
# Kern-domainobject
# ------------------------------------------------------------------------ #
class ChargePointSession:
    """
    Eén live OCPP-verbinding met een laadpaal.
    Houdt alleen sessie-state vast; transport verloopt via `WebSocketChannel`.
    """

    def __init__(
        self,
        session_id: str,
        channel: WebSocketChannel,
        parser: IOcppEndpoint,
        settings: ChargePointSettings,
    ) -> None:
        self.id = session_id
        self._channel = channel
        self._cp = parser
        self._settings = settings
        self._running = False

    # ----------------------------------------------------------- listen
    async def listen(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Session %s started", self.id)

        try:
            while True:
                raw = await self._channel.recv()
                await self._cp.route_message(raw)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Error in session %s: %s", self.id, exc, exc_info=True)
        finally:
            await self.disconnect()

    # ------------------------------------------------------ outbound RPC
    async def send_call(self, call_obj: Any) -> Any:
        """
        Stuurt een OCPP-call-object en wacht op het antwoord.
        ➜  Logt **volledig** request & response zodat we current-value-problemen
           in NotifyReport / GetBaseReport kunnen debuggen.
        """
        # -------- request-logging
        req_json = getattr(call_obj, "to_json", None)
        if callable(req_json):
            logger.info("→ CP %s | request: %s", self.id, req_json())
        else:
            logger.info("→ CP %s | request (repr): %s", self.id, repr(call_obj))

        # -------- stuur en wacht op antwoord
        response = await self._cp.call(call_obj)

        # -------- response-logging
        res_json = getattr(response, "to_json", None)
        if callable(res_json):
            logger.info("← CP %s | response: %s", self.id, res_json())
        else:
            logger.info("← CP %s | response (repr): %s", self.id, repr(response))

        return response

    # ------------------------------------------------------- disconnect
    async def disconnect(self) -> None:
        await self._channel.close()
        logger.info("Session %s closed", self.id)
        self._running = False
