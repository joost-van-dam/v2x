import { useParams, Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  fetchConfiguration,
  remoteStart,
  remoteStop,
} from "../api";
import type { ConfigKey } from "../api";
import ConfigTable from "../ui/ConfigTable";
import useBackendWs from "../hooks/useBackendWs";   // ← alleen default-export importeren

export default function ChargePointDetail() {
  const { id = "" } = useParams();
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [err, setErr] = useState<string>();
  const backendEvents = useBackendWs();

  // --------------------------------------------------- fetch config once
  useEffect(() => {
    if (!id) return;
    fetchConfiguration(id)
      .then(setConfig)
      .catch((e) => setErr(String(e)));
  }, [id]);

  // --------------------------------------------------- helpers
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

  // --------------------------------------------------- live meter-values
  const lastMv = useMemo(() => {
    return backendEvents
      .filter((e) => e.event === "MeterValues" && e.charge_point_id === id)
      .at(-1);
  }, [backendEvents, id]);

  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Charge-point {id}</h2>

      <button onClick={handleStart}>Start</button>{" "}
      <button onClick={handleStop}>Stop</button>

      {/* -------- live MV table -------- */}
      {lastMv && (
        <>
          <h3 style={{ marginTop: "2rem" }}>Last MeterValues (live)</h3>
          <pre style={{ background: "#f7f7f7", padding: "0.5rem" }}>
            {JSON.stringify(lastMv.payload, null, 2)}
          </pre>
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
