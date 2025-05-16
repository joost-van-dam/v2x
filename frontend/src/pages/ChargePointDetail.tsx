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

/* ------------------------------------------------- helpers / types ----- */
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
  /* ---------- OCPP 1.6 ---------- */
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
  /* ---------- OCPP 2.0.1 ---------- */
  if (Array.isArray(payload.evse)) {
    const rows: SampleRow[] = [];
    payload.evse.forEach((ev: any) => {
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
      );
    });
    return rows;
  }
  return [];
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

  /* -------------- helpers -------------- */
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

  /* ---- config change → /commands ---- */
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
      // update local state on success
      setConfig((prev) =>
        prev.map((c) => (c.key === key ? { ...c, value } : c))
      );
      alert("Config updated!");
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  /* -------------- latest MV -------------- */
  const lastMv = useMemo(
    () =>
      backendEvents
        .filter((e) => e.event === "MeterValues" && e.charge_point_id === id)
        .at(-1),
    [backendEvents, id]
  );

  const sortedRows: SampleRow[] = useMemo(() => {
    const rows = unravelMeterValues(lastMv?.payload);
    return rows.sort((a, b) => {
      const m = a.measurand.localeCompare(b.measurand);
      if (m !== 0) return m;
      return a.phase.localeCompare(b.phase);
    });
  }, [lastMv]);

  /* -------------- render -------------- */
  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Charge-point {id}</h2>

      <button onClick={handleStart}>Start</button>{" "}
      <button onClick={handleStop}>Stop</button>

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
      <ConfigTable
        cpId={id}
        configKeys={config}
        onConfigChange={handleConfigChange}
      />

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
        {backendEvents
          .filter((e) => e.charge_point_id === id)
          .map((e, idx) => (
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
