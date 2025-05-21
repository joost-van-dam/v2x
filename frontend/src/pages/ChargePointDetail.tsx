import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Typography,
  Button,
  Tabs,
  Tab,
  Box,
  Stack,
  TextField,
  IconButton,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  CircularProgress,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import {
  fetchConfiguration,
  remoteStart,
  remoteStop,
  fetchSettings,
  setAlias,
} from "../api";
import type { ConfigKey, CpSettings } from "../api";
import ConfigTable from "../ui/ConfigTable";
import useBackendWs from "../hooks/useBackendWs";
import type { BackendEvent } from "../hooks/useBackendWs";
import EventLogPanel from "../ui/EventLogPanel";

/* ------------------------------------------------ helpers ------ */
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
      // @ts-ignore
      return ev.payload?.status ?? JSON.stringify(ev.payload);
    case "Heartbeat":
      return new Date().toLocaleTimeString();
    case "StartTransaction":
    case "StopTransaction":
      // @ts-ignore
      return `txId=${
        ev.payload?.transaction_id ?? ev.payload?.transactionId ?? "?"
      }`;
    default:
      return JSON.stringify(ev.payload);
  }
}

/* ====================================================================== */
export default function ChargePointDetail() {
  const { id = "" } = useParams();
  const [tab, setTab] = useState(0);

  /* ------- settings ------- */
  const [settings, setSettings] = useState<CpSettings>();
  const [aliasEdit, setAliasEdit] = useState(false);
  const [aliasVal, setAliasVal] = useState("");

  /* ------- config ------- */
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [cfgLoading, setCfgLoading] = useState(false);

  /* ------- events ------- */
  const backendEvents = useBackendWs();
  const cpEvents = backendEvents.filter((e) => e.charge_point_id === id);

  /* ---------------- init ---------------- */
  useEffect(() => {
    fetchSettings(id).then((s) => {
      setSettings(s);
      setAliasVal(s.alias ?? "");
    });
  }, [id]);

  /* ---------------- helpers ---------------- */
  const refreshConfig = () => {
    setCfgLoading(true);
    fetchConfiguration(id)
      .then(setConfig)
      .finally(() => setCfgLoading(false));
  };

  const handleAliasSave = async () => {
    await setAlias(id, aliasVal);
    setAliasEdit(false);
    setSettings((p) => (p ? { ...p, alias: aliasVal } : p));
  };

  /* ------- derived data ------- */
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
  if (!settings) return <CircularProgress />;

  return (
    <>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Status & control" />
        <Tab label="Configuration" />
        <Tab label="WebSocket events" />
      </Tabs>

      {/* ---------------------------------------------------------------- */}
      {tab === 0 && (
        <>
          {/* ------- header / actions ------- */}
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems="center"
            spacing={2}
            mb={3}
          >
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Charge-point&nbsp;{id}
            </Typography>

            <Button
              variant="contained"
              color="success"
              onClick={() => remoteStart(id)}
            >
              Remote Start
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={() => remoteStop(id)}
            >
              Remote Stop
            </Button>
          </Stack>

          {/* ------- settings overview ------- */}
          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Settings
            </Typography>

            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell sx={{ width: 180, fontWeight: 600 }}>Alias</TableCell>
                  <TableCell>
                    {aliasEdit ? (
                      <Stack direction="row" spacing={1}>
                        <TextField
                          size="small"
                          value={aliasVal}
                          onChange={(e) => setAliasVal(e.target.value)}
                        />
                        <IconButton color="primary" onClick={handleAliasSave}>
                          <SaveIcon />
                        </IconButton>
                      </Stack>
                    ) : (
                      <Stack direction="row" spacing={1} alignItems="center">
                        <span>{settings.alias ?? "—"}</span>
                        <IconButton
                          size="small"
                          onClick={() => setAliasEdit(true)}
                          aria-label="edit alias"
                        >
                          <EditIcon fontSize="inherit" />
                        </IconButton>
                      </Stack>
                    )}
                  </TableCell>
                </TableRow>

                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>OCPP version</TableCell>
                  <TableCell>{settings.ocpp_version}</TableCell>
                </TableRow>

                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Active</TableCell>
                  <TableCell>{settings.active ? "Yes" : "No"}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Paper>

          {/* ------- latest events ------- */}
          <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              Latest events
            </Typography>

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, width: "30%" }}>
                    Event
                  </TableCell>
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

          {/* ------- MeterValues ------- */}
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
            </Paper>
          )}
        </>
      )}

      {/* ---------------------------------------------------------------- */}
      {tab === 1 && (
        <>
          <Stack direction="row" alignItems="center" spacing={2} mb={2}>
            <Typography variant="subtitle1">Configuration</Typography>
            <Button size="small" variant="outlined" onClick={refreshConfig}>
              Refresh
            </Button>
            {cfgLoading && <CircularProgress size={20} />}
          </Stack>

          <ConfigTable configKeys={config} onConfigChange={refreshConfig} />
        </>
      )}

      {/* ---------------------------------------------------------------- */}
      {tab === 2 && (
        <>
          <Typography variant="subtitle1" gutterBottom>
            WebSocket events (this CP)
          </Typography>

          <EventLogPanel
            events={cpEvents}
            filename={`${id}_events.json`}
            height={400}
          />
        </>
      )}
    </>
  );
}
