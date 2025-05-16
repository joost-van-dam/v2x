import { useParams, Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  fetchConfiguration,
  remoteStart,
  remoteStop,
} from "../api";
import type { ConfigKey } from "../ui/ConfigTable";
import ConfigTable from "../ui/ConfigTable";
import useBackendWs from "../hooks/useBackendWs";
import type { BackendEvent } from "../hooks/useBackendWs";   // ← type-only import!

/* ------------------------------------------------ helpers / types ------ */
interface SampleRow {
  timestamp: string;
  measurand: string;
  phase: string;
  value: string;
  unit: string;
  context: string;
  transactionId?: number;
}

function unravelMeterValues(payload: any): SampleRow[] {
  if (!payload) return [];
  // ---------- OCPP 1.6 ----------
  if (Array.isArray(payload.meter_value)) {
    const txId = payload.transaction_id ?? payload.transactionId;
    return payload.meter_value.flatMap((mvObj: any) =>
      (mvObj.sampledValue || mvObj.sampled_value || []).map((sv: any) => ({
        timestamp: mvObj.timestamp,
        measurand: sv.measurand ?? "",
        phase: sv.phase ?? "",
        value: sv.value ?? "",
        unit: sv.unit ?? "",
        context: sv.context ?? "",
        transactionId: txId,
      }))
    );
  }
  // ---------- OCPP 2.0.1 ----------
  if (Array.isArray(payload.evse)) {
    const rows: SampleRow[] = [];
    payload.evse.forEach((ev: any) =>
      ev.connector?.forEach((con: any) =>
        con.sampledValue?.forEach((sv: any) =>
          rows.push({
            timestamp: sv.timeStamp ?? sv.timestamp ?? "",
            measurand: sv.measurand ?? "",
            phase: sv.phase ?? "",
            value: sv.value ?? "",
            unit: sv.unit ?? "",
            context: sv.context ?? "",
          })
        )
      )
    );
    return rows;
  }
  return [];
}

function describeEvent(ev: BackendEvent): string {
  switch (ev.event) {
    case "StatusNotification":
      // @ts-ignore
      return ev.payload?.status ?? JSON.stringify(ev.payload);
    case "Heartbeat":
      return new Date().toLocaleTimeString();
    case "StartTransaction":
      // @ts-ignore
      return `txId=${ev.payload?.transaction_id ?? ev.payload?.transactionId ?? "?"}`;
    case "StopTransaction":
      // @ts-ignore
      return `txId=${ev.payload?.transaction_id ?? ev.payload?.transactionId ?? "?"}`;
    default:
      return JSON.stringify(ev.payload);
  }
}

/* ====================================================================== */
export default function ChargePointDetail() {
  const { id = "" } = useParams();
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [err, setErr] = useState<string>();
  const backendEvents = useBackendWs();

  /* ---------------- init config ---------------- */
  useEffect(() => {
    if (!id) return;
    fetchConfiguration(id)
      .then(setConfig)
      .catch((e) => setErr(String(e)));
  }, [id]);

  /* -------------- helpers ---------------- */
  async function handleStart() {
    try {
      await remoteStart(id);
      alert("Start sent");
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }
  async function handleStop() {
    try {
      await remoteStop(id);
      alert("Stop sent");
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleConfigChange(key: string, value: string) {
    try {
      const r = await fetch(
        `http://localhost:5062/api/v1/charge-points/${id}/commands`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "ChangeConfiguration",
            parameters: { key, value },
          }),
        }
      );
      if (!r.ok) throw new Error(await r.text());
      setConfig((prev) =>
        prev.map((c) => (c.key === key ? { ...c, value } : c))
      );
      alert("Config updated!");
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  /* -------------- live event snapshots -------------- */
  const cpEvents = backendEvents.filter((e) => e.charge_point_id === id);

  const lastByType = useMemo(() => {
    const m = new Map<string, BackendEvent>();
    cpEvents.forEach((ev) => m.set(ev.event, ev));
    return Array.from(m.values());
  }, [cpEvents]);

  const sortedRows: SampleRow[] = useMemo(() => {
    const mvEvt = lastByType.find((e) => e.event === "MeterValues");
    const rows = unravelMeterValues(mvEvt?.payload);
    return rows.sort((a, b) => {
      const m = a.measurand.localeCompare(b.measurand);
      return m !== 0 ? m : a.phase.localeCompare(b.phase);
    });
  }, [lastByType]);

  /* -------------- render -------------- */
  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Charge-point {id}</h2>

      <button onClick={handleStart}>Start</button>{" "}
      <button onClick={handleStop}>Stop</button>

      {/* -------- live key/value snapshot -------- */}
      <h3 style={{ marginTop: "2rem" }}>Latest events</h3>
      <table
        border={1}
        cellPadding={4}
        style={{ borderCollapse: "collapse", width: "100%" }}
      >
        <thead>
          <tr>
            <th style={{ width: "30%" }}>Event</th>
            <th>Value / Info</th>
          </tr>
        </thead>
        <tbody>
          {lastByType.map((ev) => (
            <tr key={ev.event}>
              <td>{ev.event}</td>
              <td>{describeEvent(ev)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* -------- live MV table -------- */}
      {sortedRows.length > 0 && (
        <>
          <h3 style={{ marginTop: "2rem" }}>Last MeterValues (live)</h3>
          <table
            border={1}
            cellPadding={4}
            style={{ borderCollapse: "collapse", width: "100%" }}
          >
            <thead>
              <tr>
                <th>Measurand</th>
                <th>Phase</th>
                <th>Value</th>
                <th>Unit</th>
                <th>Context</th>
                <th>Timestamp</th>
                <th>Tx-ID</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row, i) => (
                <tr key={i}>
                  <td>{row.measurand}</td>
                  <td>{row.phase}</td>
                  <td>{row.value}</td>
                  <td>{row.unit}</td>
                  <td>{row.context}</td>
                  <td>{row.timestamp}</td>
                  <td>{row.transactionId ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontStyle: "italic" }}>
            last updated: {new Date().toLocaleTimeString()}
          </p>
        </>
      )}

      {/* -------- configuration -------- */}
      <h3 style={{ marginTop: "2rem" }}>Configuration</h3>
      <ConfigTable cpId={id} configKeys={config} onConfigChange={handleConfigChange} />

      {/* -------- raw log viewer -------- */}
      <h3 style={{ marginTop: "2rem" }}>WebSocket events (this CP)</h3>
      <div
        style={{
          maxHeight: 200,
          overflowY: "auto",
          border: "1px solid #ccc",
          padding: 6,
        }}
      >
        {cpEvents.map((e, idx) => (
          <pre key={idx} style={{ margin: 0 }}>
            {JSON.stringify(e, null, 2)}
          </pre>
        ))}
      </div>

      <p style={{ marginTop: "2rem" }}>
        <Link to="/">← back</Link>
      </p>
    </>
  );
}
