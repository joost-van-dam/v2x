import { useEffect, useState } from "react";
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Select, MenuItem, TextField, Button, Typography
} from "@mui/material";

/* ---------------- types ---------------- */
export interface ConfigKey {
  key: string;
  readonly: boolean;
  value?: string;
}

interface Props {
  configKeys: ConfigKey[];
  onConfigChange: (key: string, value: string) => Promise<void>;
}

/* ====================================================================== */
export default function ConfigTable({ configKeys, onConfigChange }: Props) {
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  /* keep local buffer in sync */
  useEffect(() => {
    const buf: Record<string, string> = {};
    configKeys.forEach((c) => { buf[c.key] = c.value ?? ""; });
    setEditValues(buf);
  }, [configKeys]);

  const isBoolean = (v: string | undefined) => v === "true" || v === "false";

  const handleSet = async (k: string) => {
    await onConfigChange(k, editValues[k]);
  };

  return (
    <TableContainer component={Paper} sx={{ mt: 2 }}>
      <Table size="small">
        <TableHead sx={{ bgcolor: "secondary.main" }}>
          {["Key", "Access", "Current value", "Action"].map((h) => (
            <TableCell key={h} sx={{ color: "secondary.contrastText", fontWeight: 600 }}>
              {h}
            </TableCell>
          ))}
        </TableHead>

        <TableBody>
          {configKeys.map((cfg) => {
            const readOnly = cfg.readonly;
            const editableVal = editValues[cfg.key] ?? "";

            return (
              <TableRow key={cfg.key} hover>
                <TableCell sx={{ wordBreak: "break-word", width: "35%" }}>{cfg.key}</TableCell>
                <TableCell sx={{ width: "15%" }}>{readOnly ? "Read-only" : "Read/Write"}</TableCell>

                <TableCell sx={{ width: "40%" }}>
                  {readOnly ? (
                    cfg.value ?? "-"
                  ) : isBoolean(cfg.value) ? (
                    <Select
                      size="small"
                      value={editableVal}
                      onChange={(e) => setEditValues((p) => ({ ...p, [cfg.key]: e.target.value }))}
                      sx={{ minWidth: 100 }}
                    >
                      <MenuItem value="true">true</MenuItem>
                      <MenuItem value="false">false</MenuItem>
                    </Select>
                  ) : (
                    <TextField
                      size="small"
                      fullWidth
                      value={editableVal}
                      onChange={(e) => setEditValues((p) => ({ ...p, [cfg.key]: e.target.value }))}
                    />
                  )}
                </TableCell>

                <TableCell sx={{ width: "10%", textAlign: "center" }}>
                  {!readOnly && (
                    <Button variant="contained" size="small" onClick={() => handleSet(cfg.key)}>
                      Set
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            );
          })}

          {configKeys.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} align="center">
                <Typography variant="body2" color="text.secondary">
                  (no data)
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
