import { ExternalLink, ShieldQuestion } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { safeExternalUrl } from "@/lib/url";

export function SourceBadge({
  sourceName,
  sourceUrl,
  isDemo,
  testId,
}: {
  sourceName: string;
  sourceUrl?: string | null;
  isDemo?: boolean;
  testId?: string;
}) {
  const safeUrl = safeExternalUrl(sourceUrl);
  return (
    <span
      data-testid={testId ?? "source-badge"}
      className="inline-flex flex-wrap items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
    >
      <ShieldQuestion className="size-3.5" aria-hidden />
      <span>Fonte: {sourceName}</span>
      {isDemo && (
        <span className="rounded bg-amber-100 px-1.5 py-0.5 font-semibold text-amber-900 dark:bg-amber-900/50 dark:text-amber-200">
          DATI DIMOSTRATIVI
        </span>
      )}
      {safeUrl && (
        <a
          href={safeUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1 font-medium text-sky-700 underline underline-offset-2 dark:text-sky-400"
        >
          apri <ExternalLink className="size-3" aria-hidden />
        </a>
      )}
    </span>
  );
}

export function LastUpdated({ value, testId }: { value: string | null; testId?: string }) {
  return (
    <p data-testid={testId ?? "last-updated"} className="text-xs text-slate-500">
      Ultimo aggiornamento: {value ? formatDateTime(value) : "nessun dato disponibile"}
    </p>
  );
}
