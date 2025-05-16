const BASE = "http://localhost:5062/api/v1";

export async function fetchAllChargePoints(): Promise<string[]> {
  const r = await fetch(`${BASE}/get-all-charge-points`);
  if (!r.ok) throw new Error(await r.text());
  const data = (await r.json()) as { connected: string[] };
  return data.connected;
}

export interface ConfigKey {
  key: string;
  readonly: boolean;
  value?: string;
}

export async function fetchConfiguration(cpId: string): Promise<ConfigKey[]> {
  const r = await fetch(`${BASE}/charge-points/${cpId}/configuration`);
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  //  backend verpakt resultaat in `result.configuration_key`
  return (
    data.result?.configuration_key ??
    data.configuration_key ?? // fallback
    []
  );
}

export async function remoteStart(cpId: string) {
  await fetch(`${BASE}/charge-points/${cpId}/start`, { method: "POST" });
}

export async function remoteStop(cpId: string) {
  await fetch(`${BASE}/charge-points/${cpId}/stop`, { method: "POST" });
}
