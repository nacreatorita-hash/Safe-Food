import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LogOut, RefreshCw } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { endSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import { ErrorState, StatCard } from "@/components/food-alert/Primitives";
import { formatDateTime } from "@/lib/format";
import type { AdminOverview, DataSource, SyncResult } from "@/types/api";

export default function Admin() {
  const queryClient = useQueryClient();
  const overview = useQuery({
    queryKey: ["admin-overview"],
    queryFn: () => apiGet<AdminOverview>("/admin/overview"),
    retry: false,
  });
  const sources = useQuery({
    queryKey: ["data-sources"],
    queryFn: () => apiGet<DataSource[]>("/admin/sources"),
    retry: false,
  });

  const sync = useMutation({
    mutationFn: (id: string) => apiPost<SyncResult>(`/admin/sync/${id}`),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["data-sources"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
      queryClient.invalidateQueries({ queryKey: ["recalls"] });
      if (result.ok) toast.success(result.message);
      else toast.warning(result.message);
    },
    onError: () => toast.error("Sincronizzazione non riuscita"),
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="font-heading text-3xl font-extrabold tracking-tight">Area amministrazione</h1>
          <p className="max-w-3xl text-slate-600 dark:text-slate-400">
            Stato dell'ingestion, record da verificare e trigger manuali di sincronizzazione. Accesso riservato all'amministratore autenticato.
          </p>
        </div>
        <Button variant="outline" data-testid="admin-logout" onClick={() => void endSession()}>
          <LogOut className="size-4" aria-hidden /> Esci
        </Button>
      </header>

      {overview.isError && <ErrorState testId="admin-error" />}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard testId="admin-stat-recalls" label="Richiami" value={overview.data?.recalls ?? "—"} />
        <StatCard
          testId="admin-stat-to-verify"
          tone="warning"
          label="Da verificare"
          value={overview.data?.recalls_to_verify ?? "—"}
          hint="Bassa confidenza di estrazione"
        />
        <StatCard testId="admin-stat-demo" label="Record demo" value={overview.data?.demo_recalls ?? "—"} />
      </div>

      <section className="space-y-3">
        <h2 className="font-heading text-2xl font-bold tracking-tight">Fonti dati</h2>
        <div className="grid gap-3">
          {(sources.data ?? []).filter((s) => s.active).map((s) => (
            <div
              key={s.id}
              data-testid={`admin-source-${s.id}`}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800"
            >
              <div className="min-w-64">
                <p className="font-semibold">{s.name}</p>
                <p className="text-xs text-slate-500">
                  {s.source_type.toUpperCase()} · {s.schedule} · record: {s.record_count}
                </p>
                <p className="text-xs text-slate-500">
                  Ultimo successo: {s.last_successful_sync_at ? formatDateTime(s.last_successful_sync_at) : "mai"}
                </p>
                {s.last_error && (
                  <p data-testid={`admin-source-error-${s.id}`} className="mt-1 max-w-xl text-xs text-amber-700 dark:text-amber-400">
                    {s.last_error}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                data-testid={`admin-sync-${s.id}`}
                disabled={sync.isPending}
                onClick={() => sync.mutate(s.id)}
              >
                <RefreshCw className="size-4" aria-hidden /> Sincronizza ora
              </Button>
            </div>
          ))}
        </div>
      </section>

    </div>
  );
}
