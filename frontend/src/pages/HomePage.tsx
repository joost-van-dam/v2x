import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
  Typography,
  Link,
  CircularProgress,
  Divider,
} from "@mui/material";
import {
  fetchAllChargePoints,
  setChargePointActive,
} from "../api";
import type { ChargePointInfo } from "../api";
import useBackendWs from "../hooks/useBackendWs";
import EventLogPanel from "../ui/EventLogPanel";

export default function HomePage() {
  /* ---------------- state ---------------- */
  const [cps, setCps] = useState<ChargePointInfo[]>([]);
  const [err, setErr] = useState<string>();
  const [loading, setLoading] = useState(true);

  /* ---------------- live backend events ---------------- */
  const backendEvents = useBackendWs();

  /* ---------------- init CP-list ---------------- */
  useEffect(() => {
    fetchAllChargePoints()
      .then(setCps)
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  /* ---------------- toggle active ---------------- */
  const handleToggle = async (id: string, newVal: boolean) => {
    try {
      await setChargePointActive(id, newVal);
      setCps((prev) =>
        prev.map((c) => (c.id === id ? { ...c, active: newVal } : c)),
      );
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  };

  /* ---------------- filter events → alleen ‘enabled’ CP’s ---------------- */
  const activeEvents = useMemo(() => {
    const activeIds = new Set(
      cps.filter((c) => c.active).map((c) => c.id),
    );
    return backendEvents.filter((e) =>
      activeIds.has(e.charge_point_id ?? ""),
    );
  }, [backendEvents, cps]);

  /* ---------------- loading / error ---------------- */
  if (loading) return <CircularProgress />;
  if (err)
    return (
      <Typography color="error" sx={{ mt: 2 }}>
        {err}
      </Typography>
    );

  /* ---------------- render ---------------- */
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
                <TableCell sx={{ width: 220 }}>
                  {cp.alias ?? "—"}
                </TableCell>
                <TableCell sx={{ wordBreak: "break-word" }}>
                  {cp.id}
                </TableCell>
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

      {/* -------- global backend events (alleen actieve CP’s) -------- */}
      <Divider sx={{ my: 4 }} />
      <Typography variant="subtitle1" gutterBottom>
        Backend events (active charge-points)
      </Typography>
      <EventLogPanel
        events={activeEvents}
        filename="active_cp_events.json"
        height={300}
      />
    </>
  );
}
