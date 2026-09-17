import type { RiskType, Severity } from "@/types/api";

export const RISK_LABELS: Record<RiskType, string> = {
  microbiologico: "Microbiologico",
  chimico: "Chimico",
  allergeni: "Allergeni",
  fisico: "Corpo estraneo",
  etichettatura: "Etichettatura",
  altro: "Altro",
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  grave: "Rischio grave",
  attenzione: "Attenzione",
  informativo: "Informativo",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" });
}

export function daysSince(value: string): number {
  const d = new Date(value).getTime();
  return Math.max(0, Math.floor((Date.now() - d) / 86400000));
}
