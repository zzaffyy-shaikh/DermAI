export const colors = {
  patient: "#2f6bff",
  doctor: "#0ea5a0",
  admin: "#7c3aed",
  ok: "#16a34a",
  warn: "#f59e0b",
  err: "#ef4444",
  bg: "#eef2f9",
  card: "#ffffff",
  line: "#e6ebf3",
  ink: "#0b1220",
  muted: "#5b6b86",
};

export function modeColor(mode) {
  switch (mode) {
    case "normal": return colors.ok;
    case "ood": return colors.warn;
    case "healthy": return colors.patient;
    default: return "#94A3B8";
  }
}

// Format an ISO datetime ("2026-06-20T17:00:00" or "...Z") for display.
export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString([], { weekday: "short", day: "numeric", month: "short",
                                hour: "2-digit", minute: "2-digit" });
}
