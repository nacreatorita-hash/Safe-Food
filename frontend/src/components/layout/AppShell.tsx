import type { ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bell, Home, Search, ShieldAlert, Waves } from "lucide-react";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import CookieConsent from "@/components/layout/CookieConsent";
import type { AppNotification } from "@/types/api";

const NAV = [
  { label: "Home", to: "/", icon: Home, testId: "nav-home" },
  { label: "Richiami", to: "/richiami", icon: AlertTriangle, testId: "nav-recalls" },
  { label: "Mare FAO", to: "/mare", icon: Waves, testId: "nav-marine" },
];

function useUnreadCount() {
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiGet<AppNotification[]>("/notifications"),
    retry: false,
  });
  return (data ?? []).filter((n) => !n.read).length;
}

export default function AppShell({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const unread = useUnreadCount();

  function onSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get("q");
    navigate(`/richiami?q=${encodeURIComponent(String(value ?? "").trim())}`);
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-950/85">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-3 px-4 py-3 lg:px-8">
          <Link to="/" data-testid="brand-logo" className="flex shrink-0 items-center gap-2">
            <span className="grid size-9 place-items-center rounded-xl bg-[#091E3A] text-white">
              <ShieldAlert className="size-5" aria-hidden />
            </span>
            <span className="hidden font-heading text-lg font-extrabold tracking-tight text-slate-900 sm:block dark:text-slate-50">
              Food Alert <span className="text-sky-600">Italia</span>
            </span>
          </Link>

          <form onSubmit={onSearch} className="relative flex-1" role="search">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <label htmlFor="global-search" className="sr-only">
              Cerca prodotto, marca, lotto o codice a barre
            </label>
            <Input
              id="global-search"
              name="q"
              data-testid="global-search-input"
              placeholder="Cerca prodotto, marca, lotto o codice a barre"
              className="h-10 rounded-xl pl-9"
            />
          </form>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Navigazione principale">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                data-testid={`${item.testId}-desktop`}
                className={({ isActive }) =>
                  cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
                    isActive
                      ? "bg-slate-900 text-white dark:bg-sky-500 dark:text-slate-950"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <Link
            to="/notifiche"
            data-testid="notifications-button"
            aria-label={`Notifiche${unread ? `, ${unread} non lette` : ""}`}
            className="relative grid size-10 shrink-0 place-items-center rounded-xl border border-slate-200 text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Bell className="size-5" aria-hidden />
            {unread > 0 && (
              <span
                data-testid="notifications-unread-count"
                className="absolute -right-1 -top-1 grid min-w-5 place-items-center rounded-full bg-red-600 px-1 text-[11px] font-bold text-white"
              >
                {unread}
              </span>
            )}
          </Link>
        </div>
      </header>

      <main key={location.pathname} className="mx-auto w-full max-w-7xl flex-1 px-4 pb-28 pt-5 md:pb-12 lg:px-8">
        {children}
      </main>

      <footer className="border-t border-slate-200 bg-[#0B1528] px-4 pb-24 pt-8 text-slate-300 md:pb-8 lg:px-8">
        <div className="mx-auto max-w-7xl space-y-3 text-sm">
          <p className="font-heading text-base font-bold text-white">Food Alert Italia</p>
          <p data-testid="footer-disclaimer" className="max-w-4xl text-slate-400">
            Food Alert Italia è un servizio informativo indipendente e non è affiliato al Ministero della
            Salute, alla FAO o alla Commissione Europea. Le informazioni riportate non sostituiscono le
            comunicazioni ufficiali delle autorità competenti.
          </p>
          <div className="flex flex-wrap gap-4 pt-2 text-slate-400">
            <Link to="/fonti" data-testid="footer-sources-link" className="underline underline-offset-4">
              Fonti e metodologia
            </Link>
            <a href="/fonti#cookie-policy" className="underline underline-offset-4">
              Informativa cookie
            </a>
            <button
              type="button"
              onClick={() => window.dispatchEvent(new Event("food-alert:open-cookie-settings"))}
              className="underline underline-offset-4"
            >
              Gestisci cookie
            </button>
          </div>
        </div>
      </footer>

      <CookieConsent />

      <nav
        aria-label="Navigazione mobile"
        className="fixed inset-x-0 bottom-0 z-50 flex items-center justify-around border-t border-slate-200 bg-white/95 px-2 py-1.5 backdrop-blur-lg md:hidden dark:border-slate-800 dark:bg-slate-950/95"
      >
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-testid={item.testId}
            className={({ isActive }) =>
              cn(
                "flex min-w-14 flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 text-[11px] font-medium transition-colors duration-150",
                isActive ? "text-sky-700 dark:text-sky-400" : "text-slate-500 dark:text-slate-400",
              )
            }
          >
            <item.icon className="size-5" aria-hidden />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
