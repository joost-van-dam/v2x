import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  Checkbox, Typography, Link, CircularProgress, Divider,
} from "@mui/material";
import {
  fetchAllChargePoints,
  setChargePointActive,
} from "../api";
import type { ChargePointInfo } from "../api";
import useBackendWs from "../hooks/useBackendWs";
import EventLogPanel from "../ui/EventLogPanel";

export default function HomePage() {
  const [cps, setCps] = useState<ChargePointInfo[]>([]);
  const [err, setErr] = useState<string>();
  const [loading, setLoading] = useState(true);
  const backendEvents = useBackendWs();

  useEffect(() => {
    fetchAllChargePoints()
      .then(setCps)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (id: string, newVal: boolean) => {
    try {
      await setChargePointActive(id, newVal);
      setCps((prev) =>
        prev.map((c) => (c.id === id ? { ...c, active: newVal } : c))
      );
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  };

  if (loading) return <CircularProgress />;
  if (err)
    return (
      <Typography color="error" sx={{ mt: 2 }}>
        {err}
      </Typography>
    );

  return (
    <>
      <Typography variant="h5" gutterBottom>
        Connected charge-points
      </Typography>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead sx={{ bgcolor: "secondary.main" }}>
            {["Alias", "ID", "OCPP version", "Active", "Config"].map((h) => (
              <TableCell
                key={h}
                sx={{ color: "secondary.contrastText", fontWeight: 600 }}
              >
                {h}
              </TableCell>
            ))}
          </TableHead>

          <TableBody>
            {cps.map((cp) => (
              <TableRow key={cp.id} hover>
                <TableCell sx={{ width: 220 }}>{cp.alias ?? "—"}</TableCell>
                <TableCell sx={{ wordBreak: "break-word" }}>{cp.id}</TableCell>
                <TableCell>{cp.ocpp_version}</TableCell>
                <TableCell>
                  <Checkbox
                    color="primary"
                    checked={cp.active}
                    onChange={(e) => handleToggle(cp.id, e.target.checked)}
                  />
                </TableCell>
                <TableCell>
                  {cp.active ? (
                    <Link
                      component={RouterLink}
                      to={`/charge-point/${cp.id}`}
                      underline="hover"
                    >
                      open
                    </Link>
                  ) : (
                    <Typography color="text.disabled">disabled</Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}

            {cps.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography variant="body2" color="text.secondary">
                    (no charge-points connected)
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* -------- global backend events -------- */}
      <Divider sx={{ my: 4 }} />
      <Typography variant="subtitle1" gutterBottom>
        Backend events (all charge-points)
      </Typography>
      <EventLogPanel
        events={backendEvents}
        filename="all_cp_events.json"
        height={300}
      />
    </>
  );
}
