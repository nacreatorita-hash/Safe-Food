import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import RecallCard from "@/components/food-alert/RecallCard";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/food-alert/Primitives";
import { SourceBadge } from "@/components/food-alert/SourceBadge";
import type { Recall } from "@/types/api";

const RISKS: Record<string, string> = {
  tutti: "Tutti i rischi",
  microbiologico: "Microbiologico",
  chimico: "Chimico",
  allergeni: "Allergeni",
  fisico: "Corpo estraneo",
  etichettatura: "Etichettatura",
  altro: "Altro",
};

const SORTS: Record<string, string> = {
  recent: "Più recenti",
  oldest: "Meno recenti",
  name: "Nome prodotto",
};

export default function Recalls() {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") ?? "");
  const [risk, setRisk] = useState("tutti");
  const [brand, setBrand] = useState("tutte");
  const [sort, setSort] = useState("recent");

  const search = params.get("q") ?? "";

  const brands = useQuery({
    queryKey: ["recall-brands"],
    queryFn: () => apiGet<string[]>("/recalls/brands"),
    retry: false,
  });

  const url = useMemo(() => {
    const qs = new URLSearchParams({ sort, limit: "100" });
    if (search) qs.set("q", search);
    if (risk !== "tutti") qs.set("risk_type", risk);
    if (brand !== "tutte") qs.set("brand", brand);
    return `/recalls?${qs.toString()}`;
  }, [search, risk, brand, sort]);

  const recalls = useQuery({
    queryKey: ["recalls", url],
    queryFn: () => apiGet<Recall[]>(url),
    retry: false,
  });

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">Richiami e ritiri</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          Elenco dei richiami presenti nel database. Ogni scheda riporta la fonte ufficiale e il documento
          originale quando disponibile.
        </p>
        <SourceBadge sourceName="Ministero della Salute · RASFF (Commissione UE)" sourceUrl="https://www.salute.gov.it/new/it/avvisi/avvisi-e-richiami-di-prodotti-alimentari/" testId="recalls-source-badge" />
      </header>

      <form
        className="grid gap-4 rounded-2xl border border-slate-200 bg-card p-4 md:grid-cols-4 dark:border-slate-800"
        onSubmit={(e) => {
          e.preventDefault();
          setParams(query ? { q: query } : {});
        }}
      >
        <div className="md:col-span-2">
          <Label htmlFor="recalls-search">Cerca prodotto, marca, lotto, EAN</Label>
          <Input
            id="recalls-search"
            data-testid="recalls-search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Es. gorgonzola, 8001234567890, L2451A"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="recalls-risk">Tipo di rischio</Label>
          <Select value={risk} onValueChange={(value: string) => setRisk(value)}>
            <SelectTrigger id="recalls-risk" data-testid="recalls-risk-filter" className="mt-1 w-full">
              <SelectValue>{(v) => RISKS[String(v)] ?? "Tutti i rischi"}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {Object.entries(RISKS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="recalls-sort">Ordina per</Label>
          <Select value={sort} onValueChange={(value: string) => setSort(value)}>
            <SelectTrigger id="recalls-sort" data-testid="recalls-sort-filter" className="mt-1 w-full">
              <SelectValue>{(v) => SORTS[String(v)] ?? "Più recenti"}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {Object.entries(SORTS).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="md:col-span-2">
          <Label htmlFor="recalls-brand">Marca</Label>
          <Select value={brand} onValueChange={(value: string) => setBrand(value)}>
            <SelectTrigger id="recalls-brand" data-testid="recalls-brand-filter" className="mt-1 w-full">
              <SelectValue>{(v) => (String(v) === "tutte" ? "Tutte le marche" : String(v))}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tutte">Tutte le marche</SelectItem>
              {(brands.data ?? []).map((b) => (
                <SelectItem key={b} value={b}>
                  {b}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end md:col-span-2">
          <button
            type="submit"
            data-testid="recalls-search-submit"
            className="h-10 w-full rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white transition-transform duration-100 active:scale-[0.98] dark:bg-sky-500 dark:text-slate-950"
          >
            Applica ricerca
          </button>
        </div>
      </form>

      <p data-testid="recalls-result-count" className="text-sm text-slate-600 dark:text-slate-400">
        {recalls.data ? `${recalls.data.length} richiami trovati` : "Caricamento risultati…"}
      </p>

      {recalls.isLoading && <LoadingSkeleton rows={4} testId="recalls-loading" />}
      {recalls.isError && <ErrorState testId="recalls-error" />}
      {!recalls.isError && recalls.data?.length === 0 && (
        <EmptyState
          testId="recalls-empty"
          title="Nessun richiamo corrisponde ai filtri"
          description="Prova a modificare la ricerca o a rimuovere i filtri applicati."
        />
      )}
      {!recalls.isError && recalls.data && recalls.data.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {recalls.data.map((recall, index) => (
            <RecallCard key={recall.id} recall={recall} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
