import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const CONSENT_COOKIE = "food_alert_cookie_consent";
const CONSENT_MAX_AGE = 60 * 60 * 24 * 180;

type CookieConsentValue = {
  version: 1;
  necessary: true;
  analytics: boolean;
  profiling: boolean;
  updatedAt: string;
};

function readConsent(): CookieConsentValue | null {
  try {
    if (typeof document === "undefined") return null;
    const cookieString = typeof document.cookie === "string" ? document.cookie : "";
    const entry = cookieString.split("; ").find((item) => item.startsWith(`${CONSENT_COOKIE}=`));
    if (!entry) return null;

    const value = JSON.parse(decodeURIComponent(entry.slice(CONSENT_COOKIE.length + 1))) as Partial<CookieConsentValue>;
    if (value.version !== 1 || value.necessary !== true) return null;
    return {
      version: 1,
      necessary: true,
      analytics: value.analytics === true,
      profiling: value.profiling === true,
      updatedAt: typeof value.updatedAt === "string" ? value.updatedAt : new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

function saveConsent(analytics: boolean, profiling: boolean): CookieConsentValue {
  const value: CookieConsentValue = {
    version: 1,
    necessary: true,
    analytics,
    profiling,
    updatedAt: new Date().toISOString(),
  };
  try {
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${CONSENT_COOKIE}=${encodeURIComponent(JSON.stringify(value))}; Max-Age=${CONSENT_MAX_AGE}; Path=/; SameSite=Lax${secure}`;
  } catch {
    // The preference still applies for the current session if the browser blocks cookies.
  }
  return value;
}

export default function CookieConsent() {
  const [consent, setConsent] = useState<CookieConsentValue | null | undefined>(undefined);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [profiling, setProfiling] = useState(false);

  useEffect(() => {
    const saved = readConsent();
    setConsent(saved);
    setAnalytics(saved?.analytics ?? false);
    setProfiling(saved?.profiling ?? false);

    const openSettings = () => setSettingsOpen(true);
    window.addEventListener("food-alert:open-cookie-settings", openSettings);
    return () => window.removeEventListener("food-alert:open-cookie-settings", openSettings);
  }, []);

  function confirm(allowAnalytics: boolean, allowProfiling: boolean) {
    setConsent(saveConsent(allowAnalytics, allowProfiling));
    setAnalytics(allowAnalytics);
    setProfiling(allowProfiling);
    setSettingsOpen(false);
  }

  if (consent === undefined) return null;

  return (
    <>
      {consent === null && !settingsOpen && (
        <section
          role="dialog"
          aria-labelledby="cookie-consent-title"
          aria-describedby="cookie-consent-description"
          className="fixed inset-x-3 bottom-20 z-[60] mx-auto max-w-3xl rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900 md:inset-x-6 md:bottom-6"
        >
          <h2 id="cookie-consent-title" className="font-heading text-lg font-bold text-slate-950 dark:text-white">
            Cookie e privacy
          </h2>
          <p id="cookie-consent-description" className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-300">
            Food Alert Italia utilizza cookie tecnici necessari per il funzionamento dell&apos;area amministrativa e per ricordare la tua scelta. Al momento non utilizza cookie di analisi, profilazione o pubblicità.
          </p>
          <a href="/fonti#cookie-policy" className="mt-2 inline-block text-sm text-sky-700 underline underline-offset-2 dark:text-sky-400">
            Leggi l&apos;informativa cookie
          </a>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => confirm(false, false)}>
              Solo necessari
            </Button>
            <Button type="button" onClick={() => confirm(true, true)}>
              Accetta tutti
            </Button>
            <Button type="button" variant="ghost" onClick={() => setSettingsOpen(true)}>
              Personalizza
            </Button>
          </div>
        </section>
      )}

      {settingsOpen && (
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="cookie-settings-title"
          className="fixed inset-x-3 bottom-20 z-[60] mx-auto max-w-2xl rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900 md:inset-x-6 md:bottom-6"
        >
          <h2 id="cookie-settings-title" className="font-heading text-lg font-bold text-slate-950 dark:text-white">
            Personalizza i cookie
          </h2>
          <p className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-300">
            I cookie facoltativi sono disattivati per impostazione predefinita. In questa versione non è attivo alcun servizio di analisi o profilazione.
          </p>
          <div className="mt-4 space-y-3 text-sm">
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <input type="checkbox" checked disabled className="mt-1 size-4 accent-sky-600" />
              <span>
                <span className="block font-semibold text-slate-900 dark:text-white">Necessari</span>
                <span className="block text-slate-600 dark:text-slate-300">Servono per il funzionamento tecnico e per la sicurezza dell&apos;area amministrativa.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <input type="checkbox" checked={analytics} onChange={(event) => setAnalytics(event.target.checked)} className="mt-1 size-4 accent-sky-600" />
              <span>
                <span className="block font-semibold text-slate-900 dark:text-white">Analisi statistiche</span>
                <span className="block text-slate-600 dark:text-slate-300">Non attive al momento; potranno essere abilitate solo con una scelta esplicita.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <input type="checkbox" checked={profiling} onChange={(event) => setProfiling(event.target.checked)} className="mt-1 size-4 accent-sky-600" />
              <span>
                <span className="block font-semibold text-slate-900 dark:text-white">Profilazione e pubblicità</span>
                <span className="block text-slate-600 dark:text-slate-300">Non utilizzate da Food Alert Italia.</span>
              </span>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => confirm(false, false)}>
              Solo necessari
            </Button>
            <Button type="button" onClick={() => confirm(analytics, profiling)}>
              Salva preferenze
            </Button>
          </div>
        </section>
      )}
    </>
  );
}
