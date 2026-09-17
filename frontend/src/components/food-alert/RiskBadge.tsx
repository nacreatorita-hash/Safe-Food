import { AlertOctagon, AlertTriangle, FlaskConical, Info, Nut, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { RISK_LABELS, SEVERITY_LABELS } from "@/lib/format";
import type { RiskType, Severity } from "@/types/api";

const ICONS: Record<RiskType, typeof AlertTriangle> = {
  microbiologico: AlertOctagon,
  chimico: FlaskConical,
  allergeni: Nut,
  fisico: AlertTriangle,
  etichettatura: Info,
  altro: ShieldCheck,
};

const TONE: Record<Severity, string> = {
  grave: "bg-red-50 text-red-800 border-red-200 dark:bg-red-950/40 dark:text-red-200 dark:border-red-900",
  attenzione:
    "bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-900",
  informativo:
    "bg-sky-50 text-sky-900 border-sky-200 dark:bg-sky-950/40 dark:text-sky-200 dark:border-sky-900",
};

interface Props {
  riskType: RiskType;
  severity: Severity;
  className?: string;
  testId?: string;
}

// Severity is never communicated by colour alone: icon + explicit text label always present.
export default function RiskBadge({ riskType, severity, className, testId }: Props) {
  const Icon = ICONS[riskType];
  return (
    <span
      data-testid={testId ?? "risk-badge"}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        TONE[severity],
        className,
      )}
    >
      <Icon className="size-3.5 shrink-0" aria-hidden />
      <span>
        {SEVERITY_LABELS[severity]} · {RISK_LABELS[riskType]}
      </span>
    </span>
  );
}
