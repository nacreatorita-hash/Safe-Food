import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISSED_KEY = "food_alert_install_prompt_dismissed";

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches || ("standalone" in navigator && navigator.standalone === true);
}

function isAppleMobile() {
  return /iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

export default function InstallPrompt() {
  const [installEvent, setInstallEvent] = useState<InstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;

    let dismissed = false;
    try {
      dismissed = window.localStorage.getItem(DISMISSED_KEY) === "1";
    } catch {
      // Continue without persistence when storage is unavailable.
    }
    if (dismissed) return;

    const onBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as InstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);

    if (isAppleMobile()) {
      const timer = window.setTimeout(() => setVisible(true), 1800);
      return () => {
        window.clearTimeout(timer);
        window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      };
    }

    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
  }, []);

  function dismiss() {
    setVisible(false);
    try {
      window.localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // The close action still applies to the current page.
    }
  }

  async function install() {
    if (!installEvent) return;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    setInstallEvent(null);
    if (choice.outcome === "accepted") dismiss();
  }

  if (!visible) return null;

  return (
    <section
      role="dialog"
      aria-labelledby="install-app-title"
      className="fixed inset-x-3 bottom-20 z-[55] mx-auto max-w-lg rounded-2xl border border-sky-200 bg-white p-4 shadow-2xl dark:border-sky-900 dark:bg-slate-900 md:inset-x-6 md:bottom-6"
    >
      <button
        type="button"
        onClick={dismiss}
        aria-label="Chiudi invito di installazione"
        className="absolute right-3 top-3 rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
      >
        <X className="size-4" aria-hidden />
      </button>
      <div className="flex gap-3 pr-6">
        <img src="/favicon.svg" alt="" className="size-12 shrink-0 rounded-xl" />
        <div>
          <h2 id="install-app-title" className="font-heading text-base font-bold text-slate-950 dark:text-white">
            Installa Food Alert Italia
          </h2>
          <p className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-300">
            Aggiungi l&apos;app alla schermata Home per consultare rapidamente richiami e zone FAO.
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {installEvent && (
          <Button type="button" size="sm" onClick={() => void install()}>
            <Download className="size-4" aria-hidden />
            Aggiungi alla Home
          </Button>
        )}
        <Button type="button" size="sm" variant="outline" render={<Link to="/installa" />}>
          Come fare
        </Button>
        <button type="button" onClick={dismiss} className="ml-auto text-xs text-slate-500 underline underline-offset-2">
          Non ora
        </button>
      </div>
    </section>
  );
}
