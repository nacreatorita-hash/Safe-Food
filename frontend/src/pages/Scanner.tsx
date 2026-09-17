import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Camera, CameraOff, ScanLine } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Recall } from "@/types/api";

// Native BarcodeDetector (Chrome/Android) is not in TS lib yet — minimal declaration.
interface DetectedBarcode {
  rawValue: string;
  format: string;
}
interface BarcodeDetectorLike {
  detect(source: ImageBitmapSource): Promise<DetectedBarcode[]>;
}
declare global {
  interface Window {
    BarcodeDetector?: new (opts?: { formats: string[] }) => BarcodeDetectorLike;
  }
}

const EAN_RE = /^\d{8}$|^\d{12,13}$/;

export default function Scanner() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<() => void>(() => {});
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);

  const lookup = useCallback(
    async (code: string) => {
      const ean = code.trim();
      if (!EAN_RE.test(ean)) {
        toast.error("Codice non valido: servono 8, 12 o 13 cifre (EAN-8, UPC-A, EAN-13)");
        return;
      }
      setBusy(true);
      try {
        const matches = await apiGet<Recall[]>(`/recalls?q=${encodeURIComponent(ean)}&limit=5`);
        const exact = matches.find((r) => r.ean === ean);
        if (exact) {
          toast.error("ATTENZIONE: questo codice corrisponde a un prodotto richiamato");
          navigate(`/richiami/${exact.id}`);
        } else {
          toast.message("Prodotto non ancora presente nel database", {
            description: "Puoi inserirlo manualmente nella dispensa.",
          });
          navigate(`/dispensa?ean=${ean}`);
        }
      } catch {
        toast.error("Ricerca non riuscita, riprova");
      } finally {
        setBusy(false);
      }
    },
    [navigate],
  );

  const stop = useCallback(() => {
    stopRef.current();
    stopRef.current = () => {};
    setActive(false);
  }, []);

  async function start() {
    setError(null);
    const video = videoRef.current;
    if (!video) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      setActive(true);

      let cancelled = false;
      const onHit = (value: string) => {
        if (cancelled) return;
        cancelled = true;
        stop();
        void lookup(value);
      };

      if (window.BarcodeDetector) {
        const detector = new window.BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });
        const tick = async () => {
          if (cancelled) return;
          try {
            const codes = await detector.detect(video);
            if (codes[0]?.rawValue) return onHit(codes[0].rawValue);
          } catch {
            /* frame not ready */
          }
          requestAnimationFrame(() => setTimeout(tick, 120));
        };
        void tick();
        stopRef.current = () => {
          cancelled = true;
          stream.getTracks().forEach((t) => t.stop());
        };
      } else {
        const { BrowserMultiFormatReader } = await import("@zxing/browser");
        const reader = new BrowserMultiFormatReader();
        const controls = await reader.decodeFromVideoElement(video, (result) => {
          if (result) onHit(result.getText());
        });
        stopRef.current = () => {
          cancelled = true;
          controls.stop();
          stream.getTracks().forEach((t) => t.stop());
        };
      }
    } catch (e) {
      setError(
        e instanceof Error && e.name === "NotAllowedError"
          ? "Accesso alla fotocamera negato. Consenti la fotocamera oppure inserisci il codice manualmente."
          : "Fotocamera non disponibile su questo dispositivo. Inserisci il codice manualmente.",
      );
      setActive(false);
    }
  }

  useEffect(() => () => stopRef.current(), []);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <span className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-white dark:bg-sky-500 dark:text-slate-950">
          <ScanLine className="size-3.5" aria-hidden /> Scanner
        </span>
        <h1 className="font-heading text-3xl font-extrabold tracking-tight">Scansiona un codice a barre</h1>
        <p className="max-w-3xl text-slate-600 dark:text-slate-400">
          Inquadra il codice EAN-13, EAN-8 o UPC sulla confezione: l'app controlla subito se il prodotto è
          oggetto di richiamo e ti permette di salvarlo nella dispensa.
        </p>
      </header>

      <section className="grid gap-5 lg:grid-cols-12">
        <div className="space-y-3 lg:col-span-7">
          <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-950 dark:border-slate-800">
            <video
              ref={videoRef}
              data-testid="scanner-video"
              className="aspect-[4/3] w-full object-cover"
              muted
              playsInline
            />
            {active && (
              <div
                aria-hidden
                className="pointer-events-none absolute inset-x-[15%] top-1/2 h-0.5 -translate-y-1/2 bg-red-500 shadow-[0_0_12px_rgba(239,68,68,.9)]"
              />
            )}
            {!active && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-300">
                <Camera className="size-10" aria-hidden />
                <p className="text-sm">La fotocamera è spenta</p>
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            {!active ? (
              <Button data-testid="scanner-start-button" onClick={start} disabled={busy}>
                <Camera className="size-4" aria-hidden /> Avvia fotocamera
              </Button>
            ) : (
              <Button variant="outline" data-testid="scanner-stop-button" onClick={stop}>
                <CameraOff className="size-4" aria-hidden /> Ferma
              </Button>
            )}
          </div>
          {error && (
            <p
              data-testid="scanner-error"
              className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
            >
              {error}
            </p>
          )}
        </div>

        <form
          className="space-y-3 rounded-2xl border border-slate-200 bg-card p-5 lg:col-span-5 dark:border-slate-800"
          onSubmit={(e) => {
            e.preventDefault();
            void lookup(manual);
          }}
        >
          <h2 className="font-heading text-lg font-bold">Inserimento manuale</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Digita le cifre stampate sotto il codice a barre.
          </p>
          <Label htmlFor="manual-ean">Codice EAN / UPC</Label>
          <Input
            id="manual-ean"
            data-testid="scanner-manual-input"
            inputMode="numeric"
            value={manual}
            onChange={(e) => setManual(e.target.value.replace(/\D/g, ""))}
            placeholder="Es. 8001234567890"
          />
          <Button type="submit" className="w-full" data-testid="scanner-manual-submit" disabled={busy}>
            Cerca codice
          </Button>
        </form>
      </section>
    </div>
  );
}
