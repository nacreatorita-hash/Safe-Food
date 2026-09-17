import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CalendarDays, Fish, Package } from "lucide-react";
import { Button } from "@/components/ui/button";
import RiskBadge from "@/components/food-alert/RiskBadge";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { selectRecallImage } from "@/lib/recallImages";
import type { Recall } from "@/types/api";

interface Props {
  recall: Recall;
  index?: number;
  className?: string;
}

function cleanProductName(value: string): string {
  return value.replace(new RegExp("^[\\s()[\\]{}.,:;/-]+"), "").trim() || value.trim();
}

function formatExpiration(value: string | null): string | null {
  if (!value) return null;
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(value)) return value;
  return formatDate(value);
}

export default function RecallCard({ recall, index = 0, className }: Props) {
  const productName = cleanProductName(recall.product_name);
  const lots = recall.lots.filter((item) => item.lot_code.trim());
  const lotSummary = lots.map((item) => item.lot_code.trim()).join(", ");
  const expirations = Array.from(
    new Set(
      lots
        .map((item) => formatExpiration(item.expiration_date))
        .concat(formatExpiration(recall.expiration_date))
        .filter((value): value is string => Boolean(value)),
    ),
  ).join(", ");
  const image = selectRecallImage(recall);
  const fallbackImage = selectRecallImage({ ...recall, image_url: null });
  const [imageSrc, setImageSrc] = useState(image.src);
  const [isFallback, setIsFallback] = useState(image.isFallback);

  useEffect(() => {
    setImageSrc(image.src);
    setIsFallback(image.isFallback);
  }, [image.src, image.isFallback]);

  function handleImageError() {
    if (imageSrc !== fallbackImage.src) {
      setImageSrc(fallbackImage.src);
      setIsFallback(true);
    } else {
      setImageSrc("");
    }
  }
  return (
    <article
      data-testid={`recall-card-${recall.id}`}
      className={cn(
        "group flex h-full flex-col overflow-hidden rounded-[1.5rem] border border-slate-200/90 bg-card shadow-sm",
        "transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-1 hover:shadow-lg",
        "dark:border-slate-800",
        className,
      )}
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="relative h-48 w-full overflow-hidden bg-slate-100 dark:bg-slate-900">
        {imageSrc ? (
          <img
            src={imageSrc}
            alt={`${isFallback ? fallbackImage.label : image.label} per ${productName}`}
            loading="lazy"
            onError={handleImageError}
            className={cn(
              "size-full transition-transform duration-300 group-hover:scale-[1.02]",
              isFallback ? "object-cover" : "bg-white p-2 object-contain dark:bg-slate-950",
            )}
          />
        ) : (
          <div className="flex size-full items-center justify-center text-slate-400">
            <Package className="size-8" aria-hidden />
          </div>
        )}
        <span
          data-testid={`recall-image-source-${recall.id}`}
          className="absolute bottom-3 left-3 rounded-full bg-slate-950/70 px-2 py-1 text-[10px] font-semibold text-white backdrop-blur-sm"
        >
          {isFallback ? "Illustrazione standard" : "Fonte del richiamo"}
        </span>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
              {recall.brand ?? "Marca non indicata"}
            </p>
            <h3 className="mt-1 line-clamp-2 text-lg font-semibold leading-snug text-slate-900 dark:text-slate-100">
              {productName}
            </h3>
          </div>
          {recall.is_seafood && (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-sky-50 px-2 py-1 text-[11px] font-semibold text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
              <Fish className="size-3" aria-hidden /> Ittico
            </span>
          )}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <RiskBadge riskType={recall.risk_type} severity={recall.severity} testId={`recall-risk-${recall.id}`} />
        </div>

        <div
          className={cn(
            "mt-4 rounded-xl border-l-4 p-3",
            recall.severity === "grave" && "border-red-500 bg-red-50/80 dark:bg-red-950/30",
            recall.severity === "attenzione" && "border-amber-500 bg-amber-50/80 dark:bg-amber-950/30",
            recall.severity === "informativo" && "border-sky-500 bg-sky-50/80 dark:bg-sky-950/30",
          )}
        >
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
            Perché è stato richiamato
          </p>
          <p className="mt-1 line-clamp-3 text-sm font-semibold leading-5 text-slate-800 dark:text-slate-100">
            {recall.risk_description ?? "Motivo del richiamo non specificato dalla fonte."}
          </p>
        </div>

        <dl className="mt-4 grid gap-x-4 gap-y-3 text-xs text-slate-600 sm:grid-cols-2 dark:text-slate-400">
          <div className="min-w-0">
            <dt className="flex items-center gap-1.5 font-semibold text-slate-500 dark:text-slate-400">
              <CalendarDays className="size-3.5" aria-hidden /> Data richiamo
            </dt>
            <dd className="mt-1 truncate text-slate-800 dark:text-slate-200">{formatDate(recall.published_at)}</dd>
          </div>
          <div className="min-w-0">
            <dt className="font-semibold text-slate-500 dark:text-slate-400">Lotti coinvolti</dt>
            <dd className="mt-1 line-clamp-2 break-words font-mono text-slate-800 dark:text-slate-200">
              {lotSummary || "Non indicati dalla fonte"}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="font-semibold text-slate-500 dark:text-slate-400">Scadenza</dt>
            <dd className="mt-1 line-clamp-2 break-words text-slate-800 dark:text-slate-200">
              {expirations || "Non indicata dalla fonte"}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="font-semibold text-slate-500 dark:text-slate-400">Codice EAN</dt>
            <dd className="mt-1 truncate font-mono text-slate-800 dark:text-slate-200">
              {recall.ean || "Non disponibile nella fonte"}
            </dd>
          </div>
        </dl>
        {recall.is_seafood && (recall.fao_area_code || recall.production_method) && (
          <p className="text-xs font-semibold text-sky-700 dark:text-sky-300">
            {recall.fao_area_code && <span>Zona FAO {recall.fao_area_code}</span>}
            {recall.fao_area_code && recall.production_method && <span className="mx-1 text-slate-400">·</span>}
            {recall.production_method && <span>{recall.production_method}</span>}
          </p>
        )}
        <div className="mt-auto pt-3">
          <Link
            to={`/richiami/${recall.id}`}
            data-testid={`recall-open-${recall.id}`}
            className="inline-flex w-full"
          >
            <Button variant="outline" className="w-full active:scale-[0.98] transition-transform duration-100">
              Apri richiamo
            </Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
