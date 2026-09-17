import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FlaskConical, Nut, Waves } from "lucide-react";
import { apiGet } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import RecallCard from "@/components/food-alert/RecallCard";
import { EmptyState, ErrorState, LoadingSkeleton, StatCard } from "@/components/food-alert/Primitives";
import { SourceBadge } from "@/components/food-alert/SourceBadge";
import type { Recall, RecallStats } from "@/types/api";

export default function Home() {
  const recalls = useQuery({
    queryKey: ["recalls", { limit: 6 }],
    queryFn: () => apiGet<Recall[]>("/recalls?limit=6"),
    retry: false,
  });
  const stats = useQuery({
    queryKey: ["recall-stats"],
    queryFn: () => apiGet<RecallStats>("/recalls/stats"),
    retry: false,
  });
  return (
    <div className="space-y-10">
      {/* Hero — renders unconditionally, never gated on a fetch */}
      <section className="overflow-hidden rounded-3xl bg-[#091E3A] px-6 py-10 text-white lg:px-12 lg:py-14">
        <div className="grid gap-8 lg:grid-cols-12 lg:items-center">
          <div className="space-y-4 lg:col-span-7">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.2em]">
              <AlertTriangle className="size-3.5" aria-hidden /> Sicurezza alimentare in Italia
            </span>
            <h1 className="font-heading text-3xl font-black leading-tight tracking-tight sm:text-4xl lg:text-5xl">
              Richiami alimentari e provenienza del pescato.
            </h1>
            <p className="max-w-2xl text-slate-300">
              Consulta gli ultimi richiami pubblicati e scopri da quale zona FAO proviene il pesce che
              acquisti. Ogni informazione riporta sempre la fonte.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link to="/richiami" data-testid="hero-recalls-cta" className={buttonVariants({ size: "lg" })}>
                Vedi gli ultimi richiami
              </Link>
              <Link
                to="/mare"
                data-testid="hero-marine-cta"
                className={`${buttonVariants({ variant: "outline", size: "lg" })} border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white`}
              >
                Controlla zona FAO
              </Link>
            </div>
          </div>
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-white/15 bg-white/5 p-5 backdrop-blur">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-300">Informazione verificabile</p>
              <p className="mt-2 font-heading text-3xl font-black">Fonti sempre indicate</p>
              <p className="mt-2 text-sm text-slate-300">
                Ministero della Salute, RASFF e FAO con collegamento alla fonte originale.
              </p>
              <Link to="/fonti" className="mt-4 inline-flex text-sm font-semibold text-sky-300 underline underline-offset-4">
                Scopri fonti e metodologia
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Statistiche */}
      <section aria-labelledby="stats-title" className="space-y-4">
        <h2 id="stats-title" className="font-heading text-2xl font-bold tracking-tight">
          I numeri dei richiami
        </h2>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            testId="stat-last-30"
            label="Ultimi 30 giorni"
            value={stats.data?.last_30_days ?? "—"}
            hint="Richiami pubblicati"
            icon={<AlertTriangle className="size-4 text-slate-400" aria-hidden />}
          />
          <StatCard
            testId="stat-microbiological"
            tone="danger"
            label="Microbiologici"
            value={stats.data?.microbiologico ?? "—"}
            hint="Listeria, Salmonella…"
            icon={<AlertTriangle className="size-4 text-red-500" aria-hidden />}
          />
          <StatCard
            testId="stat-allergens"
            tone="warning"
            label="Allergeni"
            value={stats.data?.allergeni ?? "—"}
            hint="Non dichiarati in etichetta"
            icon={<Nut className="size-4 text-amber-600" aria-hidden />}
          />
          <StatCard
            testId="stat-chemical"
            tone="marine"
            label="Chimici"
            value={stats.data?.chimico ?? "—"}
            hint="Contaminanti e residui"
            icon={<FlaskConical className="size-4 text-sky-600" aria-hidden />}
          />
        </div>
        {stats.isError && <ErrorState testId="stats-error" />}
      </section>

      {/* Ultimi richiami */}
      <section aria-labelledby="recalls-title" className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="recalls-title" className="font-heading text-2xl font-bold tracking-tight">
            Ultimi richiami alimentari
          </h2>
        </div>
        <SourceBadge sourceName="Ministero della Salute · RASFF (Commissione UE)" sourceUrl="https://www.salute.gov.it/new/it/avvisi/avvisi-e-richiami-di-prodotti-alimentari/" testId="home-source-badge" />
        {recalls.isLoading && <LoadingSkeleton rows={3} testId="home-recalls-loading" />}
        {recalls.isError && <ErrorState testId="home-recalls-error" />}
        {!recalls.isError && recalls.data && recalls.data.length === 0 && (
          <EmptyState
            testId="home-recalls-empty"
            title="Nessun richiamo disponibile"
            description="Non ci sono richiami nel database. Avvia una sincronizzazione dall'area amministrazione."
          />
        )}
        {!recalls.isError && recalls.data && recalls.data.length > 0 && (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {recalls.data.map((recall, index) => (
              <RecallCard key={recall.id} recall={recall} index={index} />
            ))}
          </div>
        )}
        <div className="flex justify-center pt-1">
          <Link to="/richiami" data-testid="home-all-recalls-link" className={buttonVariants({ variant: "ghost" })}>
            Vedi tutti
          </Link>
        </div>
      </section>

      {/* Sezione mare */}
      <section
        aria-labelledby="marine-title"
        className="grid gap-6 overflow-hidden rounded-3xl border border-sky-200 bg-sky-50 p-6 lg:grid-cols-12 lg:p-8 dark:border-sky-900 dark:bg-sky-950/30"
      >
        <div className="space-y-3 lg:col-span-7">
          <span className="inline-flex items-center gap-2 rounded-full bg-sky-600 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-white">
            <Waves className="size-3.5" aria-hidden /> Mare e zone FAO
          </span>
          <h2 id="marine-title" className="font-heading text-2xl font-bold tracking-tight text-sky-950 dark:text-sky-100">
            Da dove arriva il tuo pesce?
          </h2>
          <p className="max-w-2xl text-sky-900 dark:text-sky-200">
            La zona FAO indicata in etichetta identifica l'area di cattura. Cerca il codice (ad esempio
            37.2.2) per vedere il mare corrispondente e le specie comuni.
          </p>
          <Link to="/mare" data-testid="marine-cta" className={buttonVariants({ size: "lg" })}>
            Controlla zona FAO
          </Link>
        </div>
        <div className="lg:col-span-5">
          <img
            src="https://images.unsplash.com/photo-1702908324995-e9a72240809a?crop=entropy&cs=srgb&fm=jpg&w=800&q=80"
            alt="Acque costiere del Mediterraneo"
            loading="lazy"
            className="h-48 w-full rounded-2xl object-cover shadow-md"
          />
        </div>
      </section>

    </div>
  );
}
