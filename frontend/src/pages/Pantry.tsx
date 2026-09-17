import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, CalendarClock, CheckCircle2, Trash2 } from "lucide-react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/food-alert/Primitives";
import { formatDate } from "@/lib/format";
import type { PantryItem, PantryStatus } from "@/types/api";

const STATUS: Record<PantryStatus, { label: string; className: string }> = {
  ok: { label: "OK", className: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  controlla_lotto: { label: "Controlla lotto", className: "bg-amber-50 text-amber-900 border-amber-200" },
  richiamato: { label: "Richiamato", className: "bg-red-50 text-red-800 border-red-200" },
  scaduto: { label: "Scaduto", className: "bg-slate-100 text-slate-700 border-slate-300" },
};

const EMPTY = { name: "", brand: "", ean: "", lot_code: "", expiration_date: "", purchase_date: "", store: "" };

export default function Pantry() {
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  // prefilled by the scanner: /dispensa?ean=...
  const [form, setForm] = useState({ ...EMPTY, ean: params.get("ean") ?? "" });

  const pantry = useQuery({
    queryKey: ["pantry"],
    queryFn: () => apiGet<PantryItem[]>("/pantry"),
    retry: false,
  });

  const add = useMutation({
    mutationFn: () =>
      apiPost<PantryItem>("/pantry", {
        name: form.name,
        brand: form.brand || null,
        ean: form.ean || null,
        lot_code: form.lot_code || null,
        expiration_date: form.expiration_date || null,
        purchase_date: form.purchase_date || null,
        store: form.store || null,
      }),
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["pantry"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      setForm(EMPTY);
      if (item.status === "richiamato") toast.error(item.status_label);
      else if (item.status === "controlla_lotto") toast.warning(item.status_label);
      else toast.success("Prodotto aggiunto alla dispensa");
    },
    onError: () => toast.error("Aggiunta non riuscita, riprova"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiDelete<void>(`/pantry/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pantry"] });
      toast.success("Prodotto rimosso");
    },
  });

  const items = pantry.data ?? [];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">La mia dispensa</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          Registra i prodotti che hai in casa con EAN e lotto: l'app verifica automaticamente se compaiono
          in un richiamo. Senza il lotto la corrispondenza non può essere dichiarata certa.
        </p>
      </header>

      <form
        className="grid gap-4 rounded-2xl border border-slate-200 bg-card p-5 md:grid-cols-3 dark:border-slate-800"
        onSubmit={(e) => {
          e.preventDefault();
          if (!form.name.trim()) {
            toast.error("Inserisci almeno il nome del prodotto");
            return;
          }
          add.mutate();
        }}
      >
        <div className="md:col-span-3">
          <h2 className="font-heading text-lg font-bold">Aggiungi un prodotto</h2>
        </div>
        {(
          [
            ["name", "Nome prodotto *", "Es. Gorgonzola DOP dolce a fette", "text"],
            ["brand", "Marca", "Es. Caseificio Val Padana", "text"],
            ["ean", "Codice EAN / barcode", "Es. 8001234567890", "text"],
            ["lot_code", "Lotto", "Es. L2451A", "text"],
            ["expiration_date", "Scadenza", "", "date"],
            ["purchase_date", "Data acquisto", "", "date"],
            ["store", "Negozio (opzionale)", "Es. Supermercato Centro", "text"],
          ] as const
        ).map(([key, label, placeholder, type]) => (
          <div key={key}>
            <Label htmlFor={`pantry-${key}`}>{label}</Label>
            <Input
              id={`pantry-${key}`}
              data-testid={`pantry-${key.replace("_", "-")}-input`}
              type={type}
              value={form[key]}
              placeholder={placeholder}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              className="mt-1"
            />
          </div>
        ))}
        <div className="flex items-end md:col-span-2">
          <Button type="submit" data-testid="pantry-add-button" disabled={add.isPending} className="w-full sm:w-auto">
            Salva nella dispensa
          </Button>
        </div>
      </form>

      {pantry.isLoading && <LoadingSkeleton rows={3} testId="pantry-loading" />}
      {pantry.isError && <ErrorState testId="pantry-error" />}
      {!pantry.isError && items.length === 0 && !pantry.isLoading && (
        <EmptyState
          testId="pantry-empty"
          title="Dispensa vuota"
          description="Aggiungi il primo prodotto con EAN e lotto per attivare il controllo sui richiami."
        />
      )}

      {items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const tone = STATUS[item.status];
            return (
              <div
                key={item.id}
                data-testid={`pantry-item-${item.id}`}
                className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-card p-4 transition-shadow duration-200 hover:shadow-md dark:border-slate-800"
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    data-testid={`pantry-status-${item.id}`}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${tone.className}`}
                  >
                    {item.status === "ok" ? (
                      <CheckCircle2 className="size-3.5" aria-hidden />
                    ) : item.status === "scaduto" ? (
                      <CalendarClock className="size-3.5" aria-hidden />
                    ) : (
                      <AlertTriangle className="size-3.5" aria-hidden />
                    )}
                    {tone.label}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label={`Rimuovi ${item.name}`}
                    data-testid={`pantry-delete-${item.id}`}
                    onClick={() => remove.mutate(item.id)}
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </Button>
                </div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">
                  {item.brand ?? "Marca non indicata"}
                </p>
                <h3 className="font-semibold leading-snug">{item.name}</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">{item.status_label}</p>
                <dl className="mt-1 space-y-0.5 text-xs text-slate-500">
                  <div>EAN: <span className="font-mono">{item.ean ?? "—"}</span></div>
                  <div>Lotto: <span className="font-mono">{item.lot_code ?? "—"}</span></div>
                  <div>Scadenza: {formatDate(item.expiration_date)}</div>
                  {item.store && <div>Negozio: {item.store}</div>}
                </dl>
                {item.matched_recall_id && (
                  <Link
                    to={`/richiami/${item.matched_recall_id}`}
                    data-testid={`pantry-recall-link-${item.id}`}
                    className="mt-auto pt-2 text-sm font-semibold text-sky-700 underline underline-offset-4 dark:text-sky-400"
                  >
                    Apri il richiamo collegato
                  </Link>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
