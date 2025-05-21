import { useEffect, useState } from "react";

/* ------------------------------------------------ types ---------------- */
export interface BackendEvent {
  event: string;
  charge_point_id?: string;
  ocpp_version?: string;
  payload?: unknown;
}

/* ------------------------------------------------ module-scope store ---- */
/** Buffer dat de *gehele* sessie blijft bestaan (tot aan pagina-refresh). */
let eventBuffer: BackendEvent[] = [];

/** Alle React-state-setters die op updates willen luisteren. */
const listeners: Array<(events: BackendEvent[]) => void> = [];

/** Eén gedeelde WebSocket-sessie voor de hele SPA. */
let ws: WebSocket | undefined;

/* ------------------------------------------------ helpers -------------- */
function broadcast() {
  // Kopie om referentie-stabiliteit te garanderen
  const snapshot = eventBuffer.slice();
  listeners.forEach((cb) => cb(snapshot));
}

function initWebSocket() {
  if (ws) return; // al opgezet

  ws = new WebSocket("ws://localhost:5062/api/ws/frontend");

  ws.onmessage = (ev) => {
    try {
      const evt = JSON.parse(ev.data) as BackendEvent;
      eventBuffer.push(evt);
      broadcast();
    } catch {
      /* ignore malformed JSON */
    }
  };

  /* NB: we sluiten de socket *niet* automatisch bij unmount:
         pas bij een volledige pagina-refresh gaat de verbinding dicht. */
}

/* ------------------------------------------------ exported hook -------- */
export default function useBackendWs(): BackendEvent[] {
  const [events, setEvents] = useState<BackendEvent[]>(() => eventBuffer);

  useEffect(() => {
    initWebSocket();

    // Subscribe
    listeners.push(setEvents);
    // On cleanup: unsubscribe
    return () => {
      const idx = listeners.indexOf(setEvents);
      if (idx >= 0) listeners.splice(idx, 1);
    };
  }, []);

  return events;
}
