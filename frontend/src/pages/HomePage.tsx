import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAllChargePoints } from "../api";

export default function HomePage() {
  const [cpIds, setCpIds] = useState<string[]>([]);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    fetchAllChargePoints()
      .then(setCpIds)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p style={{ color: "red" }}>{err}</p>;

  return (
    <>
      <h2>Connected charge-points</h2>
      <table border={1} cellPadding={6} style={{ borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Config</th>
          </tr>
        </thead>
        <tbody>
          {cpIds.map((id) => (
            <tr key={id}>
              <td style={{ wordBreak: "break-word" }}>{id}</td>
              <td>
                <Link to={`/charge-point/${id}`}>Open</Link>
              </td>
            </tr>
          ))}
          {cpIds.length === 0 && (
            <tr>
              <td colSpan={2} style={{ textAlign: "center" }}>
                (no charge-points connected)
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
