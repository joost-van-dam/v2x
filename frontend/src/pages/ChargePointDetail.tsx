import { useParams, Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { fetchConfiguration, remoteStart, remoteStop } from "../api";
import type { ConfigKey } from "../api";
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

/**
 * Zet het (v1.6 of v2.0.1) MeterValues-payload om naar platte rijen.
 */
function unravelMeterValues(payload: any): SampleRow[] {
  if (!payload) return [];

  // ---------------- OCPP 1.6  ----------------
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

  // ---------------- OCPP 2.0.1  ----------------
  if (Array.isArray(payload.evse)) {
    // v2.0.1 heeft andere structuur → gebruik evse[*].connector[*].sampledValue
    const rows: SampleRow[] = [];
    payload.evse.forEach((ev: any) => {
      ev.connector?.forEach((con: any) => {
        con.sampledValue?.forEach((sv: any) => {
          rows.push({
            timestamp: sv.timeStamp ?? sv.timestamp ?? "",
            measurand: sv.measurand ?? "",
            phase: sv.phase ?? "",
            value: sv.value ?? "",
            unit: sv.unit ?? "",
            context: sv.context ?? "",
          });
        });
      });
    });
    return rows;
  }

  return [];
}

/* ====================================================================== */
/*                           COMPONENT                                    */
/* ====================================================================== */
export default function ChargePointDetail() {
  const { id = "" } = useParams();
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [err, setErr] = useState<string>();
  const backendEvents = useBackendWs();

  /* --------------------------- init config ---------------------------- */
  useEffect(() => {
    if (!id) return;
    fetchConfiguration(id)
      .then(setConfig)
      .catch((e) => setErr(String(e)));
  }, [id]);

  /* --------------------------- helpers -------------------------------- */
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

  /* --------------------------- latest MV ------------------------------ */
  const lastMv = useMemo(
    () =>
      backendEvents
        .filter((e) => e.event === "MeterValues" && e.charge_point_id === id)
        .at(-1),
    [backendEvents, id]
  );

  const lastRows: SampleRow[] = useMemo(
    () => unravelMeterValues(lastMv?.payload),
    [lastMv]
  );

  /* --------------------------- render --------------------------------- */
  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Charge-point {id}</h2>

      <button onClick={handleStart}>Start</button>{" "}
      <button onClick={handleStop}>Stop</button>

      {/* -------- live MV table -------- */}
      {lastRows.length > 0 && (
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
              {lastRows.map((row, i) => (
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
      <ConfigTable configKeys={config} />

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
