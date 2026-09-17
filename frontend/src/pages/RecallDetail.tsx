import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ExternalLink, FileText, Share2, Waves } from "lucide-react";
import { apiGet } from "@/lib/api";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import RiskBadge from "@/components/food-alert/RiskBadge";
import { ErrorState, LoadingSkeleton } from "@/components/food-alert/Primitives";
import { SourceBadge } from "@/components/food-alert/SourceBadge";
import { formatDate } from "@/lib/format";
import { selectRecallImage } from "@/lib/recallImages";
import { safeExternalUrl } from "@/lib/url";
import type { FaoArea, Recall } from "@/types/api";

function Row({ label, value, testId }: { label: string; value: ReactNode; testId: string }) {
  const missing = value === null || value === undefined || value === "";
  return (
    <div className="flex flex-col gap-0.5 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
      <dt className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">{label}</dt>
      <dd data-testid={testId} className="text-sm text-slate-900 dark:text-slate-100">
        {missing ? <span className="text-slate-500">Non riportato nel documento ufficiale</span> : value}
      </dd>
    </div>
  );
}

const CORE_OFFICIAL_FIELDS = new Set([
  "document_date", "brand", "product_name", "osa", "lot_code", "plant_mark", "producer", "plant",
  "expiration_date", "package_size", "risk_description", "consumer_advice", "ean",
]);

const OFFICIAL_FIELD_LABELS: Record<string, string> = {
  document_date: "Data del documento",
  brand: "Marchio del prodotto",
  product_name: "Denominazione di vendita",
  osa: "Operatore del settore alimentare (OSA)",
  lot_code: "Lotto di produzione",
  plant_mark: "Marchio di identificazione dello stabilimento",
  producer: "Nome del produttore",
  plant: "Sede dello stabilimento",
  expiration_date: "Data di scadenza / TMC",
  package_size: "Peso / volume unità di vendita",
  risk_description: "Motivo del richiamo",
  consumer_advice: "Avvertenze",
  ean: "Codice EAN",
};

export default function RecallDetail() {
  const { id = "" } = useParams();
  const [lotToCheck, setLotToCheck] = useState("");
  const [lotResult, setLotResult] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["recall", id],
    queryFn: () => apiGet<Recall>(`/recalls/${id}`),
    retry: false,
  });

  const faoAreaCode = data?.fao_area_code;
  const faoArea = useQuery({
    queryKey: ["fao-area-for-recall", faoAreaCode],
    queryFn: () => apiGet<FaoArea>(`/fao/areas/${faoAreaCode}`),
    enabled: Boolean(faoAreaCode),
    retry: false,
  });

  const selectedImage = data ? selectRecallImage(data) : null;
  const selectedFallbackImage = data ? selectRecallImage({ ...data, image_url: null }) : null;
  const selectedImageSrc = selectedImage?.src ?? "";
  const selectedImageIsFallback = selectedImage?.isFallback ?? true;
  const [imageSrc, setImageSrc] = useState("");
  const [isFallback, setIsFallback] = useState(true);

  useEffect(() => {
    if (selectedImageSrc) {
      setImageSrc(selectedImageSrc);
      setIsFallback(selectedImageIsFallback);
    }
  }, [selectedImageSrc, selectedImageIsFallback]);

  function handleImageError() {
    if (selectedFallbackImage && imageSrc !== selectedFallbackImage.src) {
      setImageSrc(selectedFallbackImage.src);
      setIsFallback(true);
    } else {
      setImageSrc("");
    }
  }

  if (isLoading) return <LoadingSkeleton rows={5} testId="recall-detail-loading" />;
  if (isError || !data)
    return (
      <div className="space-y-4">
        <ErrorState testId="recall-detail-error" />
        <Link to="/richiami" className={buttonVariants({ variant: "outline" })} data-testid="recall-detail-back">
          Torna ai richiami
        </Link>
      </div>
    );

  const recall = data;
  const image = selectedImage!;
  const fallbackImage = selectedFallbackImage!;
  const sourceUrl = safeExternalUrl(recall.source_url);
  const pdfUrl = safeExternalUrl(recall.pdf_url);
  const productUrl = safeExternalUrl(recall.product_url);
  const documentUnavailable = recall.source === "Ministero della Salute"
    && !pdfUrl
    && recall.official_fields?._document_checked === "no_pdf";
  const extraOfficialFields = Object.entries(recall.official_fields ?? {}).filter(
    ([key, value]) => value && !key.startsWith("_") && !CORE_OFFICIAL_FIELDS.has(key),
  );

  function checkLot() {
    const normalized = lotToCheck.trim().toLowerCase();
    if (!normalized) {
      setLotResult("Inserisci il codice lotto riportato sulla confezione.");
      return;
    }
    const hit = recall.lots.some((l) => l.lot_code.toLowerCase() === normalized);
    setLotResult(
      hit
        ? "ATTENZIONE: il lotto inserito risulta tra quelli coinvolti nel richiamo. Non consumare il prodotto."
        : "Il lotto inserito non risulta tra quelli elencati in questo richiamo. Verifica comunque la comunicazione ufficiale.",
    );
  }

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title: recall.title, url });
      else {
        await navigator.clipboard.writeText(url);
        toast.success("Link copiato negli appunti");
      }
    } catch {
      toast.message("Condivisione annullata");
    }
  }

  return (
    <article className="space-y-6">
      <Link to="/richiami" data-testid="recall-detail-back" className="text-sm text-sky-700 underline underline-offset-4 dark:text-sky-400">
        ← Tutti i richiami
      </Link>

      <div
        data-testid="recall-alert-banner"
        className="flex flex-col gap-2 rounded-2xl border border-red-200 bg-red-50 p-5 dark:border-red-900 dark:bg-red-950/40"
      >
        <p className="font-heading text-xl font-extrabold text-red-800 dark:text-red-200">
          ATTENZIONE — Prodotto oggetto di richiamo
        </p>
        <p className="text-sm text-red-800 dark:text-red-300">
          {recall.consumer_advice ?? "Segui le indicazioni riportate nella comunicazione ufficiale."}
        </p>
      </div>

      {documentUnavailable && (
        <div
          data-testid="recall-document-unavailable"
          className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100"
        >
          <FileText className="mt-0.5 size-5 shrink-0" aria-hidden />
          <p>
            La pagina del Ministero non collega un PDF ufficiale per questo richiamo.
            I campi non presenti nella pagina non possono quindi essere estratti automaticamente.
          </p>
        </div>
      )}

      <header className="grid gap-5 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <div className="relative">
            <img
              src={imageSrc}
              alt={`${isFallback ? fallbackImage.label : image.label} per ${recall.product_name}`}
              onError={handleImageError}
              className="h-56 w-full rounded-2xl object-cover"
            />
            <span
              data-testid="recall-detail-image-source"
              className="absolute bottom-3 left-3 rounded-full bg-slate-950/70 px-2 py-1 text-[10px] font-semibold text-white backdrop-blur-sm"
            >
              {isFallback ? "Illustrazione standard" : "Fonte del richiamo"}
            </span>
          </div>
        </div>
        <div className="space-y-3 lg:col-span-8">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{recall.brand ?? "Marca non indicata"}</p>
          <h1 data-testid="recall-detail-title" className="font-heading text-3xl font-extrabold tracking-tight">
            {recall.product_name}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge riskType={recall.risk_type} severity={recall.severity} testId="recall-detail-risk" />
            {!recall.verified && (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                Da verificare — dettagli nel documento ufficiale (estrazione automatica non disponibile)
              </span>
            )}
            {recall.is_seafood && (
              <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2.5 py-1 text-xs font-semibold text-white">
                <Waves className="size-3" aria-hidden /> Prodotto ittico
              </span>
            )}
          </div>
          <p className="text-slate-700 dark:text-slate-300">{recall.risk_description}</p>
          <SourceBadge sourceName={recall.source} sourceUrl={sourceUrl} isDemo={recall.is_demo} testId="recall-detail-source" />
        </div>
      </header>

      <section className="grid gap-6 lg:grid-cols-12">
        <div className="rounded-2xl border border-slate-200 bg-card p-5 lg:col-span-7 dark:border-slate-800">
          <h2 className="font-heading text-lg font-bold">Dati del richiamo</h2>
          <dl className="mt-2">
            <Row label="Marca" value={recall.brand} testId="recall-field-brand" />
            <Row label="Denominazione commerciale" value={recall.product_name} testId="recall-field-name" />
            <Row label="Codice EAN / barcode" value={recall.ean} testId="recall-field-ean" />
            <Row
              label="Lotti coinvolti"
              value={
                recall.lots.length ? (
                  <ul className="space-y-1">
                    {recall.lots.map((lot) => (
                      <li key={`${lot.lot_code}-${lot.expiration_date ?? ""}`} className="font-mono">
                        {lot.lot_code}
                        {lot.expiration_date && <span className="ml-2 font-sans text-slate-600">· scadenza/TMC: {lot.expiration_date}</span>}
                      </li>
                    ))}
                  </ul>
                ) : null
              }
              testId="recall-field-lots"
            />
            <Row label="Data di scadenza / TMC" value={recall.expiration_date} testId="recall-field-expiration" />
            <Row label="OSA / ragione sociale" value={recall.osa} testId="recall-field-osa" />
            <Row label="Produttore" value={recall.producer} testId="recall-field-producer" />
            <Row label="Marchio identificativo stabilimento" value={recall.plant_mark} testId="recall-field-plant-mark" />
            <Row label="Stabilimento" value={recall.plant} testId="recall-field-plant" />
            <Row label="Formato confezione" value={recall.package_size} testId="recall-field-package" />
            <Row label="Data del documento ufficiale" value={recall.document_date} testId="recall-field-document-date" />
            <Row label="Data pubblicazione" value={formatDate(recall.published_at)} testId="recall-field-published" />
            <Row label="Avvertenze al consumatore" value={recall.consumer_advice} testId="recall-field-advice" />
            {recall.is_seafood && (
              <>
                <Row label="Nome scientifico" value={recall.scientific_name} testId="recall-field-scientific" />
                <Row label="Metodo di produzione" value={recall.production_method} testId="recall-field-method" />
                <Row
                  label="Zona FAO di cattura"
                  value={recall.fao_area_code ? (
                    <Link to={`/mare?zona=${recall.fao_area_code}`} className="text-sky-700 underline underline-offset-2 dark:text-sky-400">
                      FAO {recall.fao_area_code}{faoArea.data?.name_it ? ` · ${faoArea.data.name_it}` : ""}
                    </Link>
                  ) : null}
                  testId="recall-field-fao"
                />
              </>
            )}
          </dl>
        </div>

        {extraOfficialFields.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-card p-5 lg:col-span-7 dark:border-slate-800">
            <h2 className="font-heading text-lg font-bold">Altri dati dal documento ufficiale</h2>
            <dl className="mt-2">
              {extraOfficialFields.map(([key, value]) => (
                <Row key={key} label={OFFICIAL_FIELD_LABELS[key] ?? key.replaceAll("_", " ")} value={value} testId={`recall-official-field-${key}`} />
              ))}
            </dl>
          </div>
        )}

        <div className="space-y-4 lg:col-span-5">
          <div className="rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
            <h2 className="font-heading text-lg font-bold">Controlla il tuo lotto</h2>
            <Label htmlFor="lot-check" className="mt-3 block">
              Codice lotto sulla confezione
            </Label>
            <Input
              id="lot-check"
              data-testid="lot-check-input"
              value={lotToCheck}
              onChange={(e) => setLotToCheck(e.target.value)}
              placeholder="Es. L2451A"
              className="mt-1"
            />
            <Button className="mt-3 w-full" data-testid="lot-check-button" onClick={checkLot}>
              Controlla se il mio lotto è coinvolto
            </Button>
            {lotResult && (
              <p data-testid="lot-check-result" className="mt-3 rounded-xl bg-slate-100 p-3 text-sm dark:bg-slate-800">
                {lotResult}
              </p>
            )}
          </div>

          <div className="grid gap-2 rounded-2xl border border-slate-200 bg-card p-5 dark:border-slate-800">
            <h2 className="font-heading text-lg font-bold">Azioni</h2>
            <Button variant="outline" data-testid="share-button" onClick={share}>
              <Share2 className="size-4" aria-hidden /> Condividi
            </Button>
            {sourceUrl && (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noreferrer noopener"
                data-testid="official-source-link"
                className={buttonVariants({ variant: "outline" })}
              >
                <ExternalLink className="size-4" aria-hidden /> Vedi richiamo ufficiale
              </a>
            )}
            {pdfUrl && (
              <a
                href={pdfUrl}
                target="_blank"
                rel="noreferrer noopener"
                data-testid="official-pdf-link"
                className={buttonVariants({ variant: "outline" })}
              >
                <FileText className="size-4" aria-hidden /> Apri documento ufficiale
              </a>
            )}
            {productUrl && (
              <a
                href={productUrl}
                target="_blank"
                rel="noreferrer noopener"
                data-testid="product-link"
                className={buttonVariants({ variant: "ghost" })}
              >
                Vedi prodotto
              </a>
            )}
            {recall.is_seafood && recall.fao_area_code && (
              <Link
                to={`/mare?zona=${recall.fao_area_code}`}
                data-testid="fao-zone-link"
                className={buttonVariants({ variant: "ghost" })}
              >
                <Waves className="size-4" aria-hidden /> Visualizza zona di pesca {recall.fao_area_code}
              </Link>
            )}
          </div>
        </div>
      </section>
    </article>
  );
}
