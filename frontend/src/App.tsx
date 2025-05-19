import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Link,
  Container,
} from "@mui/material";
import { Routes, Route, Link as RouterLink } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ChargePointDetail from "./pages/ChargePointDetail";

/* --------------------------------------------------------- */
/* Kleuren-thema (WCAG-proof)                                */
/* --------------------------------------------------------- */
const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#399A4B",      // donker-groen
      contrastText: "#FFFFFF",
    },
    secondary: {
      main: "#3D4240",      // donker-grijs
      contrastText: "#FFFFFF",
    },
    success: { main: "#8DD783" },
    background: {
      default: "#FFFFFF",
      paper: "#FFFFFF",
    },
    text: {
      primary: "#000000",
      secondary: "#6A6E6B",
    },
    grey: {
      500: "#6A6E6B",
      300: "#AAB0AA",
    },
  },
  typography: {
    fontFamily: '"Roboto","Helvetica","Arial",sans-serif',
  },
});

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      {/* ---------- top-bar ---------- */}
      <AppBar position="static" color="secondary">
        <Toolbar sx={{ gap: 2 }}>
          <Link
            component={RouterLink}
            to="/"
            variant="h6"
            underline="none"
            sx={{ fontWeight: 600, color: "common.white" }}
          >
            CSMS&nbsp;Debug&nbsp;UI
          </Link>
        </Toolbar>
      </AppBar>

      {/* ---------- pagina-inhoud ---------- */}
      <Container maxWidth="lg" sx={{ mt: 3, mb: 6 }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/charge-point/:id" element={<ChargePointDetail />} />
        </Routes>
      </Container>
    </ThemeProvider>
  );
}
