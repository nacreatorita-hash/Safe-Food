import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, FlaskConical, Nut, RefreshCw, ShieldCheck, Waves } from "lucide-react";
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
      <section className="overflow-hidden rounded-[2rem] border border-white/80 bg-white/75 px-6 py-10 text-slate-950 shadow-[0_24px_70px_-32px_rgba(15,23,42,0.45)] backdrop-blur-2xl sm:px-10 lg:px-16 lg:py-14 dark:border-slate-700/80 dark:bg-slate-900/70 dark:text-white">
        <div className="mx-auto max-w-4xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-sky-700 dark:text-sky-300">
            Sicurezza alimentare in Italia
          </p>
          <h1 className="mt-4 font-heading text-4xl font-black leading-[1.05] tracking-[-0.04em] sm:text-5xl lg:text-6xl">
            Richiami alimentari e provenienza del pescato.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg dark:text-slate-300">
            Consulta gli ultimi richiami pubblicati e scopri da quale zona FAO proviene il pesce che
            acquisti. Ogni informazione riporta sempre la fonte.
          </p>
          <div className="flex flex-wrap justify-center gap-3 pt-7">
            <Link to="/richiami" data-testid="hero-recalls-cta" className={buttonVariants({ size: "lg" })}>
              Vedi gli ultimi richiami
            </Link>
            <Link
              to="/mare"
              data-testid="hero-marine-cta"
              className={`${buttonVariants({ variant: "outline", size: "lg" })} border-slate-300 bg-white/60 hover:bg-white dark:border-slate-600 dark:bg-slate-900/40 dark:hover:bg-slate-800`}
            >
              Controlla zona FAO
            </Link>
          </div>
          <div className="mt-9 flex flex-wrap justify-center gap-x-7 gap-y-3 border-t border-slate-200/80 pt-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-300">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="size-4 text-sky-600 dark:text-sky-300" aria-hidden />
              Fonti ufficiali sempre indicate
            </span>
            <span className="inline-flex items-center gap-2">
              <RefreshCw className="size-4 text-sky-600 dark:text-sky-300" aria-hidden />
              Aggiornamenti automatici
            </span>
            <Link to="/fonti" className="font-semibold text-sky-700 underline underline-offset-4 dark:text-sky-300">
              Fonti e metodologia
            </Link>
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
