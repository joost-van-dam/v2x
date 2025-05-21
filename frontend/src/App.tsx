import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Link,
  Container,
  Box,
  IconButton,
} from "@mui/material";
import { Description } from "@mui/icons-material";
import { Routes, Route, Link as RouterLink } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ChargePointDetail from "./pages/ChargePointDetail";
import logoWhite from "./assets/logo_white.svg";

/* --------------------------------------------------------- */
/* Kleuren-schema (WCAG-proof)                               */
/* --------------------------------------------------------- */
const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#399A4B", contrastText: "#FFFFFF" },
    secondary: { main: "#3D4240", contrastText: "#FFFFFF" },
    success: { main: "#8DD783" },
    background: { default: "#FFFFFF", paper: "#FFFFFF" },
    text: { primary: "#000000", secondary: "#6A6E6B" },
    grey: { 500: "#6A6E6B", 300: "#AAB0AA" },
  },
  typography: { fontFamily: '"Roboto","Helvetica","Arial",sans-serif' },
});

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      {/* ---------- top-bar ---------- */}
      <AppBar position="static" color="secondary">
        <Toolbar sx={{ gap: 2 }}>
          <Box component="img" src={logoWhite} alt="logo" sx={{ height: 48 }} />

          <Link
            component={RouterLink}
            to="/"
            variant="h6"
            underline="none"
            sx={{ fontWeight: 600, color: "common.white", flexGrow: 1 }}
          >
            OCPP Gateway / CSMS
          </Link>

          {/* link naar Swagger-UI */}
          <IconButton
            component="a"
            href="http://localhost:5062/docs"
            target="_blank"
            rel="noopener noreferrer"
            title="Open API docs"
            sx={{ color: "common.white" }}
          >
            <Description />
          </IconButton>
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
