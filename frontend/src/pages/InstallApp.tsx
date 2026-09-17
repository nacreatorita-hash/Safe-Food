import { CheckCircle2, MoreVertical, Plus, Share2, Smartphone } from "lucide-react";
import { Link } from "react-router-dom";

const steps = [
  {
    title: "Chrome su Android",
    icon: MoreVertical,
    items: [
      "Apri Food Alert Italia in Chrome.",
      "Tocca il menu ⋮ in alto a destra.",
      "Scegli “Installa app” oppure “Aggiungi alla schermata Home”.",
      "Conferma: l’icona Food Alert Italia comparirà tra le app del telefono.",
    ],
  },
  {
    title: "Safari su iPhone o iPad",
    icon: Share2,
    items: [
      "Apri Food Alert Italia in Safari.",
      "Tocca il pulsante Condividi (quadrato con la freccia verso l’alto).",
      "Scorri e seleziona “Aggiungi alla schermata Home”.",
      "Lascia attivo “Apri come app”, se disponibile, e tocca “Aggiungi”.",
    ],
  },
  {
    title: "Chrome su iPhone o iPad",
    icon: Smartphone,
    items: [
      "Apri il sito in Chrome e tocca Condividi.",
      "Seleziona “Aggiungi alla schermata Home”.",
      "Conferma con “Aggiungi”.",
    ],
  },
];

export default function InstallApp() {
  return (
    <div className="space-y-8">
      <header className="max-w-3xl space-y-3">
        <div className="flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-14 rounded-2xl" />
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-sky-700 dark:text-sky-400">Food Alert Italia</p>
            <h1 className="font-heading text-3xl font-extrabold tracking-tight">Aggiungi l&apos;app alla schermata Home</h1>
          </div>
        </div>
        <p className="text-slate-600 dark:text-slate-400">
          Food Alert Italia è una web app: non serve scaricarla da uno store. Aggiungendola alla Home avrai un&apos;icona dedicata e un accesso rapido alle funzioni pubbliche.
        </p>
      </header>

      <section className="rounded-3xl border border-sky-200 bg-sky-50 p-5 dark:border-sky-900/60 dark:bg-sky-950/30">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-sky-700 dark:text-sky-400" aria-hidden />
          <div>
            <h2 className="font-heading text-lg font-bold">Installazione sicura e gratuita</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              L&apos;installazione crea un collegamento alla web app. Non modifica il telefono e non richiede un account per consultare le pagine pubbliche.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3" aria-label="Guide di installazione">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <article key={step.title} className="rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Icon className="size-5 text-sky-600" aria-hidden />
                <h2 className="font-heading text-lg font-bold">{step.title}</h2>
              </div>
              <ol className="mt-4 space-y-3 text-sm leading-5 text-slate-600 dark:text-slate-300">
                {step.items.map((item, index) => (
                  <li key={item} className="flex gap-2">
                    <span className="grid size-5 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-200">{index + 1}</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
            </article>
          );
        })}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
        <div className="flex items-start gap-3">
          <Plus className="mt-0.5 size-5 text-sky-600" aria-hidden />
          <div>
            <h2 className="font-heading text-lg font-bold">Se non compare il pulsante</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Usa la guida del browser: su Android apri il menu ⋮; su iPhone e iPad usa Condividi. Se avevi già aggiunto una versione precedente, rimuovi il vecchio collegamento e aggiungilo di nuovo per aggiornare l&apos;icona.
            </p>
          </div>
        </div>
      </section>

      <p className="text-sm text-slate-500 dark:text-slate-400">
        Per le fonti e le informazioni sul servizio consulta <Link to="/fonti" className="text-sky-700 underline underline-offset-2 dark:text-sky-400">Fonti e metodologia</Link>.
      </p>
    </div>
  );
}
