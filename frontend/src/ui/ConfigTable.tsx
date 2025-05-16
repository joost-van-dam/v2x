import type { ConfigKey } from "../api";   // ← type-only import

export default function ConfigTable({ configKeys }: { configKeys: ConfigKey[] }) {
  return (
    <table
      border={1}
      cellPadding={4}
      style={{ borderCollapse: "collapse", width: "100%" }}
    >
      <thead>
        <tr>
          <th style={{ width: "60%" }}>Key</th>
          <th style={{ width: "20%" }}>Access</th>
          <th style={{ width: "20%" }}>Value</th>
        </tr>
      </thead>
      <tbody>
        {configKeys.map((cfg) => (
          <tr key={cfg.key}>
            <td style={{ wordBreak: "break-word" }}>{cfg.key}</td>
            <td>{cfg.readonly ? "Read-Only" : "Read/Write"}</td>
            <td style={{ wordBreak: "break-word" }}>
              {cfg.value ?? <em>(null)</em>}
            </td>
          </tr>
        ))}
        {configKeys.length === 0 && (
          <tr>
            <td colSpan={3} style={{ textAlign: "center" }}>
              (no data)
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
