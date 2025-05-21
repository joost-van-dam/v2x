const BASE = "http://localhost:5062/api/v1";

/* ---------------- types ---------------- */
export interface ChargePointInfo {
  id: string;
  ocpp_version: string;
  active: boolean;
  alias?: string | null;
}

export interface CpSettings {
  id: string;
  ocpp_version: string;
  active: boolean;
  alias?: string | null;
}

export interface ConfigKey {
  key: string;
  readonly: boolean;
  value?: string;
}

/* ---------------- helpers ---------------- */
async function getJson<T>(url: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

/* ---------------- list / settings ---------------- */
export async function fetchAllChargePoints(
  active?: boolean
): Promise<ChargePointInfo[]> {
  const qp = active === undefined ? "" : `?active=${active}`;
  const data = await getJson<{ connected: ChargePointInfo[] }>(
    `${BASE}/get-all-charge-points${qp}`
  );
  return data.connected;
}

export async function fetchSettings(cpId: string): Promise<CpSettings> {
  return getJson<CpSettings>(`${BASE}/charge-points/${cpId}/settings`);
}

/* ---------------- alias ---------------- */
export async function setAlias(cpId: string, alias: string) {
  await fetch(`${BASE}/charge-points/${cpId}/set-alias`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ alias }),
  });
}

/* ---------------- active toggle ---------------- */
export async function setChargePointActive(id: string, active: boolean) {
  const ep = active ? "enable" : "disable";
  await fetch(`${BASE}/charge-points/${id}/${ep}`, { method: "POST" });
}

/* ---------------- configuration + start/stop ---------------- */
export async function fetchConfiguration(cpId: string): Promise<ConfigKey[]> {
  const data = await getJson<any>(`${BASE}/charge-points/${cpId}/configuration`);
  return data.result?.configuration_key ?? data.configuration_key ?? [];
}

export const remoteStart = (cpId: string) =>
  fetch(`${BASE}/charge-points/${cpId}/start`, { method: "POST" });

export const remoteStop = (cpId: string) =>
  fetch(`${BASE}/charge-points/${cpId}/stop`, { method: "POST" });
