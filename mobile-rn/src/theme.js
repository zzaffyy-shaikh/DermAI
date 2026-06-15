export const colors = {
  patient: "#2563EB",
  doctor: "#0D9488",
  admin: "#7C3AED",
  ok: "#16A34A",
  warn: "#EA580C",
  err: "#DC2626",
  bg: "#F1F5F9",
  card: "#FFFFFF",
  line: "#E2E8F0",
  ink: "#0F172A",
  muted: "#64748B",
};

export function modeColor(mode) {
  switch (mode) {
    case "normal": return colors.ok;
    case "ood": return colors.warn;
    case "healthy": return colors.patient;
    default: return "#94A3B8";
  }
}
