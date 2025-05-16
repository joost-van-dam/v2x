import { useEffect, useRef, useState } from "react";

export interface BackendEvent {
  event: string;
  charge_point_id?: string;
  ocpp_version?: string;
  payload?: unknown;
}

export default function useBackendWs() {
  const [messages, setMessages] = useState<BackendEvent[]>([]);
  const wsRef = useRef<WebSocket>();

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:5062/api/ws/frontend");
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as BackendEvent;
        setMessages((prev) => [...prev, data]);
      } catch {
        /* ignore */
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  return messages;
}
