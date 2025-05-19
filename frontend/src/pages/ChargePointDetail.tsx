import { useParams, Link as RouterLink } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import {
  Typography,
  Button,
  Stack,
  Divider,
  Link,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Box,
} from "@mui/material";
import { fetchConfiguration, remoteStart, remoteStop } from "../api";
import ConfigTable from "../ui/ConfigTable";
import type { ConfigKey } from "../ui/ConfigTable";
import useBackendWs from "../hooks/useBackendWs";
import type { BackendEvent } from "../hooks/useBackendWs"; // ← type-only import

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

/**
 * Normaliseert OCPP 1.6 én 2.0.1 payloads naar één tabel-shape.
 */
function unravelMeterValues(payload: any): SampleRow[] {
  if (!payload) return [];

  /* ---------- OCPP 1.6 ---------- */
  if (Array.isArray(payload.meter_value)) {
    const txId = payload.transaction_id ?? payload.transactionId;
    return payload.meter_value.flatMap((mv: any) =>
      (mv.sampledValue || mv.sampled_value || []).map((sv: any) => ({
        timestamp: mv.timestamp,
        measurand: sv.measurand ?? "",
        phase: sv.phase ?? "",
        value: sv.value ?? "",
        unit: sv.unit ?? "",
        context: sv.context ?? "",
        transactionId: txId,
      })),
    );
  }

  /* ---------- OCPP 2.0.1 ---------- */
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
          }),
        ),
      ),
    );
    return rows;
  }

  return [];
}

function describeEvent(ev: BackendEvent): string {
  switch (ev.event) {
    case "StatusNotification":
      // @ts-ignore because payload is loosely typed
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
    fetchConfiguration(id).then(setConfig).catch((e) => setErr(String(e)));
  }, [id]);

  /* ---------------- actions ---------------- */
  const handleStart = () => remoteStart(id).catch(alert);
  const handleStop = () => remoteStop(id).catch(alert);

  async function handleConfigChange(key: string, value: string) {
    try {
      const r = await fetch(`http://localhost:5062/api/v1/charge-points/${id}/commands`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "ChangeConfiguration",
          parameters: { key, value },
        }),
      });
      if (!r.ok) throw new Error(await r.text());

      setConfig((prev) => prev.map((c) => (c.key === key ? { ...c, value } : c)));
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    }
  }

  /* ---------------- live event snapshots ---------------- */
  const cpEvents = backendEvents.filter((e) => e.charge_point_id === id);

  const lastByType: BackendEvent[] = useMemo(() => {
    const m = new Map<string, BackendEvent>();
    cpEvents.forEach((ev) => m.set(ev.event, ev));
    return Array.from(m.values());
  }, [cpEvents]);

  const sortedRows: SampleRow[] = useMemo(() => {
    const mvEvt = lastByType.find((e) => e.event === "MeterValues");
    const rows = unravelMeterValues(mvEvt?.payload);
    return rows.sort((a, b) => {
      const meas = a.measurand.localeCompare(b.measurand);
      return meas !== 0 ? meas : a.phase.localeCompare(b.phase);
    });
  }, [lastByType]);

  /* ---------------- render ---------------- */
  if (err) return <Typography color="error">{err}</Typography>;

  return (
    <>
      {/* ---------- header + buttons ---------- */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems="center"
        spacing={2}
        mb={2}
      >
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Charge-point&nbsp;{id}
        </Typography>

        <Button variant="contained" color="success" onClick={handleStart}>
          Remote Start
        </Button>
        <Button variant="contained" color="secondary" onClick={handleStop}>
          Remote Stop
        </Button>
      </Stack>

      {/* ---------- latest event snapshot ---------- */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Latest events
        </Typography>

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, width: "30%" }}>Event</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Value / Info</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {lastByType.map((ev) => (
              <TableRow key={ev.event}>
                <TableCell>{ev.event}</TableCell>
                <TableCell>{describeEvent(ev)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      {/* ---------- MeterValues ---------- */}
      {sortedRows.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Last MeterValues (live)
          </Typography>

          <Table size="small">
            <TableHead>
              <TableRow>
                {[
                  "Measurand",
                  "Phase",
                  "Value",
                  "Unit",
                  "Context",
                  "Timestamp",
                  "Tx-ID",
                ].map((h) => (
                  <TableCell key={h} sx={{ fontWeight: 600 }}>
                    {h}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>

            <TableBody>
              {sortedRows.map((row, i) => (
                <TableRow key={i}>
                  <TableCell>{row.measurand}</TableCell>
                  <TableCell>{row.phase}</TableCell>
                  <TableCell>{row.value}</TableCell>
                  <TableCell>{row.unit}</TableCell>
                  <TableCell>{row.context}</TableCell>
                  <TableCell>{row.timestamp}</TableCell>
                  <TableCell>{row.transactionId ?? ""}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Typography
            variant="caption"
            sx={{ fontStyle: "italic", display: "block", mt: 1 }}
          >
            last updated: {new Date().toLocaleTimeString()}
          </Typography>
        </Paper>
      )}

      {/* ---------- configuration ---------- */}
      <Typography variant="subtitle1" gutterBottom>
        Configuration
      </Typography>
      <ConfigTable configKeys={config} onConfigChange={handleConfigChange} />

      {/* ---------- raw WS log ---------- */}
      <Divider sx={{ my: 4 }} />
      <Typography variant="subtitle1" gutterBottom>
        WebSocket events (this CP)
      </Typography>

      <Paper
        variant="outlined"
        sx={{ maxHeight: 240, overflow: "auto", p: 1, mb: 4 }}
      >
        {cpEvents.map((e, idx) => (
          <Box component="pre" key={idx} sx={{ m: 0, fontSize: 12 }}>
            {JSON.stringify(e, null, 2)}
          </Box>
        ))}
      </Paper>

      <Link component={RouterLink} to="/" underline="hover">
        ← back
      </Link>
    </>
  );
}
