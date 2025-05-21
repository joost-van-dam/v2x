import {
    Paper,
    Stack,
    Button,
    Checkbox,
    FormControlLabel,
    TextField,
    Box,
    MenuItem,
  } from "@mui/material";
  import Select from "@mui/material/Select";
  import type { SelectChangeEvent } from "@mui/material/Select";
  import DownloadIcon from "@mui/icons-material/Download";
  import PauseIcon from "@mui/icons-material/Pause";
  import PlayArrowIcon from "@mui/icons-material/PlayArrow";
  import { useEffect, useMemo, useState } from "react";
  
  export interface EventLogPanelProps {
    events: unknown[];
    height?: number;
    filename?: string;
  }
  
  /* ---------------------------------------------------------------- */
  /* kleurpaletten per theme                                          */
  /* ---------------------------------------------------------------- */
  interface ThemeSpec {
    bg: string;
    font: string;
    base: string;      // { } , :
    key: string;       // "foo":
    string: string;    // "bar"
    number: string;    // 42
    boolNull: string;  // true / false / null
  }
  
  const THEMES: Record<string, ThemeSpec> = {
    None: {
      bg: "#fafafa",
      font: "Roboto, sans-serif",
      base: "#000",
      key: "#000",
      string: "#000",
      number: "#000",
      boolNull: "#000",
    },
    Monokai: {
      bg: "#272822",
      font: "Menlo, monospace",
      base: "#F8F8F2",
      key: "#66D9EF",
      string: "#E6DB74",
      number: "#AE81FF",
      boolNull: "#F92672",
    },
    "Solarized Dark": {
      bg: "#002b36",
      font: "Menlo, monospace",
      base: "#839496",
      key: "#268BD2",
      string: "#2AA198",
      number: "#D33682",
      boolNull: "#CB4B16",
    },
    "Solarized Light": {
      bg: "#fdf6e3",
      font: "Menlo, monospace",
      base: "#657b83",
      key: "#268BD2",
      string: "#2AA198",
      number: "#D33682",
      boolNull: "#CB4B16",
    },
    Dracula: {
      bg: "#282a36",
      font: "Menlo, monospace",
      base: "#f8f8f2",
      key: "#8be9fd",
      string: "#f1fa8c",
      number: "#bd93f9",
      boolNull: "#ff79c6",
    },
    Gruvbox: {
      bg: "#282828",
      font: "Menlo, monospace",
      base: "#ebdbb2",
      key: "#fabd2f",
      string: "#b8bb26",
      number: "#d3869b",
      boolNull: "#fe8019",
    },
  };
  
  /* ---------------------------------------------------------------- */
  /* heel simpele JSON-highlighter                                     */
  /* ---------------------------------------------------------------- */
  function highlightJson(src: string, t: ThemeSpec): string {
    const esc = (s: string) =>
      s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return esc(src).replace(
      /("(?:\\.|[^"\\])*"(?:\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (m) => {
        if (/^"/.test(m)) {
          // key vs string?
          const isKey = /:$/.test(m);
          return `<span style="color:${isKey ? t.key : t.string}">${m}</span>`;
        }
        if (/true|false|null/.test(m)) {
          return `<span style="color:${t.boolNull}">${m}</span>`;
        }
        // number
        return `<span style="color:${t.number}">${m}</span>`;
      },
    );
  }
  
  export default function EventLogPanel({
    events,
    height = 240,
    filename = "events.json",
  }: EventLogPanelProps) {
    /* ---------------- state ---------------- */
    const [paused, setPaused] = useState(false);
    const [pretty, setPretty] = useState(false);
    const [theme, setTheme] = useState<string>("None");
    const [filter, setFilter] = useState("");
    const [log, setLog] = useState<unknown[]>([]);
  
    /* ---------------- buffer ---------------- */
    useEffect(() => {
      if (!paused) setLog(events);
    }, [events, paused]);
  
    /* ---------------- filtering ---------------- */
    const visible = useMemo(() => {
      const needle = filter.toLowerCase();
      return log.filter((e) =>
        JSON.stringify(e).toLowerCase().includes(needle),
      );
    }, [log, filter]);
  
    /* ---------------- handlers ---------------- */
    const handleTheme = (e: SelectChangeEvent<string>) => setTheme(e.target.value);
  
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
    const spec = THEMES[theme];
  
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 1,
          bgcolor: spec.bg,
          color: spec.base,
          fontFamily: spec.font,
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
            sx={{ color: "inherit" }}
          />
  
          <Select
            size="small"
            value={theme}
            onChange={handleTheme}
            sx={{ minWidth: 150, color: "inherit" }}
          >
            {Object.keys(THEMES).map((t) => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </Select>
  
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
          }}
        >
          {visible.map((e, i) => {
            const json = JSON.stringify(e, null, pretty ? 2 : 0);
            const html = highlightJson(json, spec);
            return (
              <Box
                key={i}
                component="pre"
                sx={{ m: 0 }}
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          })}
        </Box>
      </Paper>
    );
  }
  