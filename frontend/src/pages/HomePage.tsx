import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchAllChargePoints,
  setChargePointActive,
} from "../api";
import type { ChargePointInfo } from "../api";   // ← type-only import

export default function HomePage() {
  const [cps, setCps] = useState<ChargePointInfo[]>([]);
  const [err, setErr] = useState<string>();

  /* ------- initial fetch ------- */
  useEffect(() => {
    fetchAllChargePoints()
      .then(setCps)
      .catch((e) => setErr(String(e)));
  }, []);

  /* ------- toggle active ------- */
  async function handleToggle(id: string, newVal: boolean) {
    try {
      await setChargePointActive(id, newVal);
      setCps((prev) =>
        prev.map((c) => (c.id === id ? { ...c, active: newVal } : c))
      );
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Connected charge-points</h2>
      <table
        border={1}
        cellPadding={6}
        style={{ borderCollapse: "collapse", width: "100%" }}
      >
        <thead>
          <tr>
            <th>ID</th>
            <th>OCPP version</th>
            <th>Active</th>
            <th>Config</th>
          </tr>
        </thead>
        <tbody>
          {cps.map((cp) => (
            <tr key={cp.id}>
              <td style={{ wordBreak: "break-word" }}>{cp.id}</td>
              <td>{cp.ocpp_version}</td>
              <td style={{ textAlign: "center" }}>
                <input
                  type="checkbox"
                  checked={cp.active}
                  onChange={(e) => handleToggle(cp.id, e.target.checked)}
                />
              </td>
              <td>
                {cp.active ? (
                  <Link to={`/charge-point/${cp.id}`}>Open</Link>
                ) : (
                  <span style={{ color: "#aaa" }}>disabled</span>
                )}
              </td>
            </tr>
          ))}
          {cps.length === 0 && (
            <tr>
              <td colSpan={4} style={{ textAlign: "center" }}>
                (no charge-points connected)
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
