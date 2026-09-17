import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { StatCard } from "@/components/food-alert/Primitives";
import type { AppNotification, PantryItem } from "@/types/api";

export default function Profile() {
  const pantry = useQuery({
    queryKey: ["pantry"],
    queryFn: () => apiGet<PantryItem[]>("/pantry"),
    retry: false,
  });
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiGet<AppNotification[]>("/notifications"),
    retry: false,
  });

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">Profilo</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          In questa versione l'app è consultabile senza account: dispensa, notifiche e preferenze sono
          salvate sul server dell'applicazione. L'autenticazione email/password, Google e Apple è già
          prevista nell'architettura.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard testId="profile-stat-pantry" label="Prodotti in dispensa" value={pantry.data?.length ?? "—"} />
        <StatCard
          testId="profile-stat-attention"
          tone="warning"
          label="Da controllare"
          value={(pantry.data ?? []).filter((i) => i.status !== "ok").length}
        />
        <StatCard
          testId="profile-stat-notifications"
          tone="danger"
          label="Notifiche non lette"
          value={(notifications.data ?? []).filter((n) => !n.read).length}
        />
        <StatCard testId="profile-stat-account" label="Account" value="Ospite" hint="Login non richiesto" />
      </div>

      <section className="grid gap-4 md:grid-cols-2">
        {[
          ["La mia dispensa", "Prodotti salvati e stato dei richiami", "/dispensa", "profile-link-pantry"],
          ["Notifiche", "Avvisi sui prodotti che hai registrato", "/notifiche", "profile-link-notifications"],
          ["Zone FAO seguite", "Consulta le aree di pesca e i dati ambientali", "/mare", "profile-link-marine"],
          ["Fonti e metodologia", "Da dove arrivano i dati mostrati", "/fonti", "profile-link-sources"],
        ].map(([title, text, href, testId]) => (
          <div key={href} className="rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
            <h2 className="font-heading text-lg font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{text}</p>
            <Link to={href} data-testid={testId} className={`${buttonVariants({ variant: "outline" })} mt-3`}>
              Apri
            </Link>
          </div>
        ))}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
        <h2 className="font-heading text-lg font-semibold">Privacy e dati</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Non vengono raccolti dati personali identificativi. I prodotti salvati restano associati a
          questa installazione dell'applicazione e possono essere eliminati singolarmente dalla dispensa.
        </p>
      </section>
    </div>
  );
}
