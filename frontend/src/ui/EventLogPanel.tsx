import {
    Paper,
    Stack,
    Button,
    Checkbox,
    FormControlLabel,
    TextField,
    Box,
  } from "@mui/material";
  import DownloadIcon from "@mui/icons-material/Download";
  import PauseIcon from "@mui/icons-material/Pause";
  import PlayArrowIcon from "@mui/icons-material/PlayArrow";
  import { useEffect, useMemo, useState } from "react";
  
  export interface EventLogPanelProps {
    events: unknown[];
    height?: number;
    filename?: string;
  }
  
  export default function EventLogPanel({
    events,
    height = 240,
    filename = "events.json",
  }: EventLogPanelProps) {
    /* ---------------- state ---------------- */
    const [paused, setPaused] = useState(false);
    const [pretty, setPretty] = useState(false);
    const [dark, setDark] = useState(false);
    const [filter, setFilter] = useState("");
    const [log, setLog] = useState<unknown[]>([]);
  
    /*  – buffer wordt alleen ververst als we niet gepauzeerd zijn */
    useEffect(() => {
      if (!paused) setLog(events);
    }, [events, paused]);
  
    /*  – filteren + formatten                               */
    const visible = useMemo(() => {
      const needle = filter.toLowerCase();
      return log.filter((e) => JSON.stringify(e).toLowerCase().includes(needle));
    }, [log, filter]);
  
    /* ---------------- helpers ---------------- */
    const handleExport = () => {
      const blob = new Blob([JSON.stringify(visible, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), {
        href: url,
        download: filename,
      });
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    };
  
    /* ---------------- render ---------------- */
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 1,
          bgcolor: dark ? "#222" : "background.paper",
          color: dark ? "grey.300" : "text.primary",
        }}
      >
        {/* controls */}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems="center"
          mb={1}
        >
          <Button
            size="small"
            variant="contained"
            startIcon={paused ? <PlayArrowIcon /> : <PauseIcon />}
            onClick={() => setPaused((p) => !p)}
          >
            {paused ? "Unpause" : "Pause"}
          </Button>
  
          <Button
            size="small"
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleExport}
          >
            Export
          </Button>
  
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={pretty}
                onChange={(e) => setPretty(e.target.checked)}
              />
            }
            label="Pretty"
          />
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={dark}
                onChange={(e) => setDark(e.target.checked)}
              />
            }
            label="Dark"
          />
  
          <TextField
            size="small"
            label="Filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            sx={{ minWidth: 180 }}
          />
        </Stack>
  
        {/* log list */}
        <Box
          sx={{
            maxHeight: height,
            overflow: "auto",
            fontSize: 12,
            whiteSpace: "pre",
          }}
        >
          {visible.map((e, i) => (
            <Box key={i} component="pre" sx={{ m: 0 }}>
              {pretty ? JSON.stringify(e, null, 2) : JSON.stringify(e)}
            </Box>
          ))}
        </Box>
      </Paper>
    );
  }
  