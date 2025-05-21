import { useState } from "react";
import { Paper, Box, Stack, Button } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";

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
  const [paused, setPaused] = useState(false);
  const visible = paused ? events.slice() : events; // shallow copy bij pauze

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(events, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Paper variant="outlined" sx={{ p: 1 }}>
      <Stack direction="row" spacing={1} mb={1}>
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
      </Stack>

      <Box
        component="pre"
        sx={{
          maxHeight: height,
          overflow: "auto",
          m: 0,
          fontSize: 12,
          bgcolor: "#fafafa",
        }}
      >
        {visible.map((e, i) => (
          <div key={i}>{JSON.stringify(e)}</div>
        ))}
      </Box>
    </Paper>
  );
}
