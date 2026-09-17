import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "neutral",
  testId,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  tone?: "neutral" | "danger" | "warning" | "marine" | "success";
  testId: string;
}) {
  const tones: Record<string, string> = {
    neutral: "border-slate-200 bg-card dark:border-slate-800",
    danger: "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30",
    warning: "border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30",
    marine: "border-sky-200 bg-sky-50 dark:border-sky-900 dark:bg-sky-950/30",
    success: "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30",
  };
  return (
    <div
      data-testid={testId}
      className={cn(
        "rounded-2xl border p-4 transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-md",
        tones[tone],
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
        {icon}
      </div>
      <p className="mt-2 font-heading text-3xl font-extrabold tabular-nums text-slate-900 dark:text-slate-50">
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  testId,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  testId: string;
}) {
  return (
    <div
      data-testid={testId}
      className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 p-8 text-center dark:border-slate-700 dark:bg-slate-900/40"
    >
      <h3 className="font-heading text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-600 dark:text-slate-400">{description}</p>
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({ testId = "error-state" }: { testId?: string }) {
  return (
    <div
      data-testid={testId}
      className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center dark:border-amber-900 dark:bg-amber-950/30"
    >
      <p className="font-semibold text-amber-900 dark:text-amber-200">Dati temporaneamente non disponibili</p>
      <p className="mt-1 text-sm text-amber-800 dark:text-amber-300">
        La fonte non ha risposto. Riprova più tardi: il resto dell'applicazione resta consultabile.
      </p>
    </div>
  );
}

export function LoadingSkeleton({ rows = 3, testId = "loading-skeleton" }: { rows?: number; testId?: string }) {
  return (
    <div data-testid={testId} className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-2xl bg-slate-200/70 dark:bg-slate-800/70" />
      ))}
    </div>
  );
}
