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

export default function RecallCard({ recall, index = 0, className }: Props) {
  const lot = recall.lots[0]?.lot_code;
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
        "group flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-card shadow-xs",
        "transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-1 hover:shadow-lg",
        "dark:border-slate-800",
        className,
      )}
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="relative h-44 w-full overflow-hidden bg-slate-50 dark:bg-slate-900">
        {imageSrc ? (
          <img
            src={imageSrc}
            alt={`${isFallback ? fallbackImage.label : image.label} per ${recall.product_name}`}
            loading="lazy"
            onError={handleImageError}
            className="size-full bg-white p-2 object-contain transition-transform duration-300 group-hover:scale-[1.02] dark:bg-slate-950"
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
        <div className="absolute left-3 top-3">
          <RiskBadge riskType={recall.risk_type} severity={recall.severity} testId={`recall-risk-${recall.id}`} />
        </div>
        {recall.is_seafood && (
          <span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-full bg-sky-600 px-2 py-1 text-[11px] font-semibold text-white">
            <Fish className="size-3" aria-hidden /> Ittico
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
          {recall.brand ?? "Marca non indicata"}
        </p>
        <h3 className="text-lg font-semibold leading-snug text-slate-900 dark:text-slate-100">
          {recall.product_name}
        </h3>
        <p className="line-clamp-2 text-sm text-slate-600 dark:text-slate-400">
          {recall.risk_description ?? "Motivo del richiamo non specificato dalla fonte."}
        </p>
        <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <CalendarDays className="size-3.5" aria-hidden />
            <dt className="sr-only">Data richiamo</dt>
            <dd>{formatDate(recall.published_at)}</dd>
          </div>
          {lot && (
            <div className="flex items-center gap-1.5">
              <dt className="font-medium">Lotto:</dt>
              <dd className="font-mono">{lot}</dd>
            </div>
          )}
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
