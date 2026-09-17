import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { BellRing, MailCheck } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/food-alert/Primitives";
import { formatDateTime } from "@/lib/format";
import type { AppNotification } from "@/types/api";

const TYPE_LABEL: Record<AppNotification["type"], string> = {
  richiamo_prodotto: "Richiamo prodotto",
  lotto_corrispondente: "Lotto corrispondente",
  marca_seguita: "Marca seguita",
  zona_fao: "Zona FAO",
  ambientale: "Allerta ambientale",
};

export default function Notifications() {
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiGet<AppNotification[]>("/notifications"),
    retry: false,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => apiPost<AppNotification>(`/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAll = useMutation({
    mutationFn: () => apiPost<{ updated: number }>("/notifications/read-all"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("Tutte le notifiche sono state segnate come lette");
    },
  });

  const items = notifications.data ?? [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-3xl font-extrabold tracking-tight">Notifiche</h1>
          <p className="text-slate-600 dark:text-slate-400">
            Avvisi generati quando un prodotto salvato corrisponde a un richiamo.
          </p>
        </div>
        <Button variant="outline" data-testid="mark-all-read-button" onClick={() => markAll.mutate()}>
          <MailCheck className="size-4" aria-hidden /> Segna tutte come lette
        </Button>
      </header>

      {notifications.isLoading && <LoadingSkeleton rows={3} testId="notifications-loading" />}
      {notifications.isError && <ErrorState testId="notifications-error" />}
      {!notifications.isError && !notifications.isLoading && items.length === 0 && (
        <EmptyState
          testId="notifications-empty"
          title="Nessuna notifica"
          description="Aggiungi prodotti alla dispensa: riceverai un avviso se uno di essi viene richiamato."
        />
      )}

      <ul className="space-y-3">
        {items.map((n) => (
          <li
            key={n.id}
            data-testid={`notification-${n.id}`}
            className={`rounded-2xl border p-4 transition-colors duration-150 ${
              n.read
                ? "border-slate-200 bg-card dark:border-slate-800"
                : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30"
            }`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <BellRing className="size-4 text-slate-500" aria-hidden />
              <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-white dark:bg-sky-500 dark:text-slate-950">
                {TYPE_LABEL[n.type]}
              </span>
              <span className="text-xs text-slate-500">{formatDateTime(n.created_at)}</span>
              {!n.read && (
                <span className="rounded-full bg-red-600 px-2 py-0.5 text-[11px] font-bold text-white">NON LETTA</span>
              )}
            </div>
            <p className="mt-2 font-semibold">{n.title}</p>
            <p className="text-sm text-slate-600 dark:text-slate-400">{n.body}</p>
            <div className="mt-3 flex flex-wrap gap-3">
              {n.recall_id && (
                <Link
                  to={`/richiami/${n.recall_id}`}
                  data-testid={`notification-recall-link-${n.id}`}
                  className="text-sm font-semibold text-sky-700 underline underline-offset-4 dark:text-sky-400"
                >
                  Apri il richiamo
                </Link>
              )}
              {!n.read && (
                <button
                  type="button"
                  data-testid={`notification-read-${n.id}`}
                  onClick={() => markRead.mutate(n.id)}
                  className="text-sm font-semibold text-slate-600 underline underline-offset-4 dark:text-slate-300"
                >
                  Segna come letta
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
