import { useEffect, useState } from "react";

/* ------------------------------------------------ types --------------- */
export interface ConfigKey {
  key: string;
  readonly: boolean;
  value?: string;
}

interface Props {
  cpId: string;
  configKeys: ConfigKey[];
  onConfigChange: (key: string, value: string) => Promise<void>;
}

/* ====================================================================== */
/*                           COMPONENT                                    */
/* ====================================================================== */
export default function ConfigTable({ cpId, configKeys, onConfigChange }: Props) {
  // local edit-buffer
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  useEffect(() => {
    const init: Record<string, string> = {};
    configKeys.forEach((c) => (init[c.key] = c.value ?? ""));
    setEditValues(init);
  }, [configKeys]);

  /* --------------------------- helpers -------------------------------- */
  const isBoolean = (v: string | undefined) => v === "true" || v === "false";

  async function handleSet(k: string) {
    const newVal = editValues[k];
    await onConfigChange(k, newVal);
  }

  /* --------------------------- render --------------------------------- */
  return (
    <table
      border={1}
      cellPadding={4}
      style={{ borderCollapse: "collapse", width: "100%" }}
    >
      <thead>
        <tr>
          <th style={{ width: "35%" }}>Key</th>
          <th style={{ width: "15%" }}>Access</th>
          <th style={{ width: "40%" }}>Current&nbsp;Value</th>
          <th style={{ width: "10%" }}>Action</th>
        </tr>
      </thead>
      <tbody>
        {configKeys.map((cfg) => {
          const readOnly = cfg.readonly;
          const editableVal = editValues[cfg.key] ?? "";

          return (
            <tr key={cfg.key}>
              <td style={{ wordBreak: "break-word" }}>{cfg.key}</td>
              <td>{readOnly ? "Read-Only" : "Read/Write"}</td>
              <td>
                {readOnly ? (
                  cfg.value ?? "-"
                ) : isBoolean(cfg.value) ? (
                  <select
                    value={editableVal}
                    onChange={(e) =>
                      setEditValues((p) => ({ ...p, [cfg.key]: e.target.value }))
                    }
                  >
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                ) : (
                  <input
                    style={{ width: "100%" }}
                    value={editableVal}
                    onChange={(e) =>
                      setEditValues((p) => ({ ...p, [cfg.key]: e.target.value }))
                    }
                  />
                )}
              </td>
              <td style={{ textAlign: "center" }}>
                {!readOnly && (
                  <button onClick={() => handleSet(cfg.key)}>Set</button>
                )}
              </td>
            </tr>
          );
        })}
        {configKeys.length === 0 && (
          <tr>
            <td colSpan={4} style={{ textAlign: "center" }}>
              (no data)
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
