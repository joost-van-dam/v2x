import { Routes, Route, Link } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ChargePointDetail from "./pages/ChargePointDetail";

export default function App() {
  return (
    <>
      <header style={{ padding: "1rem", background: "#222", color: "#fff" }}>
        <h1>CSMS Debug UI</h1>
        <Link to="/" style={{ color: "#61dafb" }}>
          Home
        </Link>
      </header>

      <main style={{ maxWidth: 1024, margin: "0 auto", padding: "1rem" }}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/charge-point/:id" element={<ChargePointDetail />} />
        </Routes>
      </main>
    </>
  );
}
