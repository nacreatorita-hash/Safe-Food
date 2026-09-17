import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Fish, MapPinned, Waves } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import FaoMap from "@/components/marine/FaoMap";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/food-alert/Primitives";
import { LastUpdated, SourceBadge } from "@/components/food-alert/SourceBadge";
import type { FaoArea, FaoGeometry, FaoOverview } from "@/types/api";

export default function Marine() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("zona") ?? "37";
  const [codeInput, setCodeInput] = useState(selected);
  const selectZone = useCallback(
    (code: string) => {
      setCodeInput(code);
      setParams({ zona: code });
    },
    [setParams],
  );

  const areas = useQuery({
    queryKey: ["fao-areas"],
    queryFn: () => apiGet<FaoArea[]>("/fao/areas"),
    retry: false,
    staleTime: 60 * 60 * 1000,
  });
  const list = areas.data ?? [];
  const area = list.find((a) => a.code === selected);
  const children = list.filter((a) => a.parent_code === selected);
  const ancestors: FaoArea[] = [];
  for (let cur = area; cur?.parent_code; ) {
    const p = list.find((a) => a.code === cur!.parent_code);
    if (!p) break;
    ancestors.unshift(p);
    cur = p;
  }
  // overview layer: children when they exist, else the siblings of the selection
  const overviewParent = children.length > 0 ? selected : area?.parent_code ?? null;
  const overviewUrl = overviewParent ? `/fao/overview?parent=${overviewParent}` : "/fao/overview?level=1";

  const overview = useQuery({
    queryKey: ["fao-overview", overviewUrl],
    queryFn: () => apiGet<FaoOverview>(overviewUrl),
    retry: false,
    enabled: !!areas.data,
    staleTime: 60 * 60 * 1000,
  });
  const geometry = useQuery({
    queryKey: ["fao-geometry", selected],
    queryFn: () => apiGet<FaoGeometry>(`/fao/areas/${selected}/geometry`),
    retry: false,
    enabled: !!area,
    staleTime: 60 * 60 * 1000,
  });
  const majors = list.filter((a) => a.level === 1);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-sky-600 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-white">
          <Waves className="size-3.5" aria-hidden /> Mare e zone FAO
        </span>
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">Zone di pesca FAO</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          Tutte le {list.length || "…"} aree, sottozone e divisioni ufficiali FAO (CWP). Inserisci il codice
          riportato in etichetta per individuare l'area di cattura del pescato.
        </p>
      </header>

      <form
        className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-card p-4 dark:border-slate-800"
        onSubmit={(e) => {
          e.preventDefault();
          selectZone(codeInput.trim());
        }}
      >
        <div className="min-w-56 flex-1">
          <Label htmlFor="fao-code">Inserisci codice FAO</Label>
          <Input
            id="fao-code"
            data-testid="fao-code-input"
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="Es. 37.2.2 oppure 27.4"
            className="mt-1"
          />
        </div>
        <Button type="submit" data-testid="fao-search-button">
          Cerca zona
        </Button>
      </form>

      <div className="flex flex-wrap gap-2" data-testid="fao-zone-chips">
        {majors.map((a) => (
          <button
            key={a.code}
            type="button"
            data-testid={`fao-chip-${a.code}`}
            onClick={() => selectZone(a.code)}
            className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors duration-150 ${
              a.code === selected || ancestors[0]?.code === a.code
                ? "border-sky-600 bg-sky-600 text-white"
                : "border-slate-200 bg-card text-slate-600 hover:bg-slate-100 dark:border-slate-800 dark:text-slate-300"
            }`}
          >
            FAO {a.code} · {a.name_it}
          </button>
        ))}
      </div>

      {areas.isLoading && <LoadingSkeleton rows={2} testId="fao-loading" />}
      {areas.isError && <ErrorState testId="fao-error" />}

      {area ? (
        <section
          data-testid="fao-zone-detail"
          className="space-y-4 rounded-3xl border border-sky-200 bg-sky-50 p-6 dark:border-sky-900 dark:bg-sky-950/30"
        >
          <nav aria-label="Gerarchia della zona" data-testid="fao-hierarchy" className="flex flex-wrap items-center gap-1 text-sm text-sky-900 dark:text-sky-200">
            {[...ancestors, area].map((a, i, arr) => (
              <span key={a.code} className="inline-flex items-center gap-1">
                {i > 0 && <ChevronRight className="size-3.5" aria-hidden />}
                <button
                  type="button"
                  data-testid={`fao-crumb-${a.code}`}
                  onClick={() => selectZone(a.code)}
                  className={i === arr.length - 1 ? "font-bold" : "underline underline-offset-2"}
                >
                  {a.level_label} <span className="font-mono">{a.code}</span> — {a.name_it}
                </button>
              </span>
            ))}
          </nav>
          <h2 data-testid="fao-zone-name" className="font-heading text-2xl font-bold text-sky-950 dark:text-sky-50">
            FAO {area.code} · {area.name_it}
          </h2>
          <p className="text-sky-900 dark:text-sky-200">
            {area.name_en !== area.name_it && <span className="text-sky-700 dark:text-sky-300">{area.name_en} · </span>}
            {area.ocean}
          </p>
          {children.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-700 dark:text-sky-300">
                {children[0].level_label === "Sottozona" ? "Sottozone" : "Suddivisioni"} ({children.length})
              </p>
              <div className="mt-2 flex flex-wrap gap-2" data-testid="fao-children">
                {children.map((c) => (
                  <button
                    key={c.code}
                    type="button"
                    data-testid={`fao-child-${c.code}`}
                    onClick={() => selectZone(c.code)}
                    className="rounded-lg border border-sky-300 bg-white px-2.5 py-1 text-xs font-semibold text-sky-900 transition-colors hover:bg-sky-100 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100"
                  >
                    <span className="font-mono">{c.code}</span> {c.name_it}
                  </button>
                ))}
              </div>
            </div>
          )}
          {area.common_species.length > 0 && (
            <p className="text-sm text-sky-900 dark:text-sky-200">
              <Fish className="mr-1 inline size-4" aria-hidden />
              Specie comuni: {area.common_species.join(", ")}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <SourceBadge sourceName={area.source_name} sourceUrl={area.source_url} testId="fao-source-badge" />
            <LastUpdated value={area.retrieved_at} testId="fao-retrieved" />
          </div>
        </section>
      ) : (
        !areas.isLoading && (
          <EmptyState
            testId="fao-not-found"
            title={`Zona FAO ${selected} non presente nell'elenco ufficiale`}
            description="Verifica il codice riportato in etichetta (es. 37.2.1) oppure seleziona un'area principale."
          />
        )
      )}

      <section aria-labelledby="map-title" className="space-y-3">
        <h2 id="map-title" className="font-heading text-2xl font-bold tracking-tight">
          <MapPinned className="mr-2 inline size-5 text-sky-600" aria-hidden />
          Mappa delle zone FAO
        </h2>
        <FaoMap
          overview={overview.data}
          selectedCode={selected}
          selectedGeometry={geometry.data?.geometry}
          onSelectZone={selectZone}
        />
        <p className="text-xs text-slate-500">
          Geometrie ufficiali FAO (CWP) dal GeoServer FAO; i contorni delle zone circostanti sono semplificati
          per la visualizzazione. Seleziona una zona per consultarne codice e denominazione.
        </p>
      </section>
    </div>
  );
}
