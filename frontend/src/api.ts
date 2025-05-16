const BASE = "http://localhost:5062/api/v1";

/* -------- types -------- */
export interface ChargePointInfo {
  id: string;
  ocpp_version: string;
  active: boolean;
}

export interface ConfigKey {
  key: string;
  readonly: boolean;
  value?: string;
}

/* -------- charge-point list -------- */
export async function fetchAllChargePoints(): Promise<ChargePointInfo[]> {
  const r = await fetch(`${BASE}/get-all-charge-points`);
  if (!r.ok) throw new Error(await r.text());
  const data = (await r.json()) as { connected: ChargePointInfo[] };
  return data.connected;
}

/* -------- enable / disable -------- */
export async function setChargePointActive(
  id: string,
  active: boolean
): Promise<void> {
  const ep = active ? "enable" : "disable";
  const r = await fetch(`${BASE}/charge-points/${id}/${ep}`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
}

/* -------- configuration + start/stop (ongewijzigd) -------- */
export async function fetchConfiguration(cpId: string): Promise<ConfigKey[]> {
  const r = await fetch(`${BASE}/charge-points/${cpId}/configuration`);
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return (
    data.result?.configuration_key ??
    data.configuration_key ??
    []
  );
}

export async function remoteStart(cpId: string) {
  await fetch(`${BASE}/charge-points/${cpId}/start`, { method: "POST" });
}

export async function remoteStop(cpId: string) {
  await fetch(`${BASE}/charge-points/${cpId}/stop`, { method: "POST" });
}
