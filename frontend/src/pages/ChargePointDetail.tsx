import { useParams, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  fetchConfiguration,
  remoteStart,
  remoteStop,
} from "../api";
import type { ConfigKey } from "../api";    // ← type-only import
import ConfigTable from "../ui/ConfigTable";

export default function ChargePointDetail() {
  const { id = "" } = useParams();
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    if (!id) return;
    fetchConfiguration(id)
      .then(setConfig)
      .catch((e) => setErr(String(e)));
  }, [id]);

  async function handleStart() {
    try {
      await remoteStart(id);
      alert("Start sent");
    } catch (e) {
      alert(e);
    }
  }

  async function handleStop() {
    try {
      await remoteStop(id);
      alert("Stop sent");
    } catch (e) {
      alert(e);
    }
  }

  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Charge-point {id}</h2>

      <button onClick={handleStart}>Start</button>{" "}
      <button onClick={handleStop}>Stop</button>

      <h3 style={{ marginTop: "2rem" }}>Configuration</h3>
      <ConfigTable configKeys={config} />

      <p style={{ marginTop: "2rem" }}>
        <Link to="/">← back</Link>
      </p>
    </>
  );
}
