import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  Typography,
  Button,
  Tabs,
  Tab,
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
  Snackbar,
  Alert,
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

/* ------------------------------------------------ snackbar helper ------ */
const useSnack = () => {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const show = useCallback((m: string) => {
    setMsg(m);
    setOpen(true);
  }, []);
  return {
    Snack: (
      <Snackbar
        open={open}
        autoHideDuration={2500}
        onClose={() => setOpen(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert severity="success" variant="filled" sx={{ width: "100%" }}>
          {msg}
        </Alert>
      </Snackbar>
    ),
    show,
  };
};

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
      }))
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
          })
        )
      )
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

  /* ------- snackbar ------- */
  const { Snack, show } = useSnack();

  /* ------- settings ------- */
  const [settings, setSettings] = useState<CpSettings>();
  const [aliasEdit, setAliasEdit] = useState(false);
  const [aliasVal, setAliasVal] = useState("");

  /* ------- config ------- */
  const [config, setConfig] = useState<ConfigKey[]>([]);
  const [cfgLoading, setCfgLoading] = useState(true);

  /* ------- events ------- */
  const backendEvents = useBackendWs();
  const cpEvents = backendEvents.filter((e) => e.charge_point_id === id);

  /* ---------------- init ---------------- */
  useEffect(() => {
    fetchSettings(id).then((s) => {
      setSettings(s);
      setAliasVal(s.alias ?? "");
    });

    fetchConfiguration(id)
      .then(setConfig)
      .finally(() => setCfgLoading(false));
  }, [id]);

  /* ---------------- helpers ---------------- */
  const refreshConfig = useCallback(() => {
    setCfgLoading(true);
    fetchConfiguration(id)
      .then(setConfig)
      .finally(() => setCfgLoading(false));
  }, [id]);

  const handleAliasSave = async () => {
    await setAlias(id, aliasVal);
    setAliasEdit(false);
    setSettings((p) => (p ? { ...p, alias: aliasVal } : p));
    show("Alias saved");
  };

  const handleConfigChange = async (key: string, value: string) => {
    await fetch(`http://localhost:5062/api/v1/charge-points/${id}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "ChangeConfiguration",
        parameters: { key, value },
      }),
    });
    show("Configuration updated");
    refreshConfig();
  };

  /* ------- react on backend config events ------- */
  useEffect(() => {
    const last = cpEvents.at(-1);
    if (last?.event === "ConfigurationChanged") {
      show("Configuration changed (CP)");
    }
  }, [cpEvents, show]);

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

  const tabSx = {
    fontSize: 16,
    fontWeight: 600,
    textTransform: "none" as const,
    minWidth: 160,
    "&:hover": { bgcolor: "action.hover" },
  };

  return (
    <>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3 }}
        textColor="primary"
        indicatorColor="primary"
      >
        <Tab label="Status & control" sx={tabSx} />
        <Tab label="Configuration" sx={tabSx} />
        <Tab label="WebSocket events" sx={tabSx} />
      </Tabs>

      {/* ---------------------------------------------------------------- */}
      {tab === 0 && (
        <>
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
              onClick={async () => {
                await remoteStart(id);
                show("Remote-start sent");
              }}
            >
              Remote Start
            </Button>
            <Button
              variant="contained"
              color="secondary"
              onClick={async () => {
                await remoteStop(id);
                show("Remote-stop sent");
              }}
            >
              Remote Stop
            </Button>
          </Stack>

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

      {tab === 1 && (
        <>
          <Stack direction="row" alignItems="center" spacing={2} mb={2}>
            <Typography variant="subtitle1">Configuration</Typography>
            <Button size="small" variant="outlined" onClick={refreshConfig}>
              Refresh
            </Button>
            {cfgLoading && <CircularProgress size={20} />}
          </Stack>

          <ConfigTable configKeys={config} onConfigChange={handleConfigChange} />
        </>
      )}

      {tab === 2 && (
        <>
          <Typography variant="subtitle1" gutterBottom>
            WebSocket events (this CP)
          </Typography>

          <EventLogPanel
            events={cpEvents}
            filename={`${id}_events.json`}
            height="80vh"
            width="90%"
          />
        </>
      )}

      {Snack}
    </>
  );
}
