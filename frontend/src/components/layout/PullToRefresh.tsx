import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

const TRIGGER_DISTANCE = 76;
const MAX_DISTANCE = 116;

function isInteractiveTarget(target: EventTarget | null) {
  return target instanceof Element && Boolean(
    target.closest("a, button, input, textarea, select, [role='button'], [data-pull-refresh-ignore]"),
  );
}

export default function PullToRefresh() {
  const [distance, setDistance] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const distanceRef = useRef(0);
  const startYRef = useRef<number | null>(null);
  const trackingRef = useRef(false);

  useEffect(() => {
    if (!window.matchMedia("(pointer: coarse)").matches) return;

    const onTouchStart = (event: TouchEvent) => {
      if (window.scrollY > 0 || isInteractiveTarget(event.target)) return;

      const startY = event.touches[0]?.clientY;
      if (startY === undefined) return;

      startYRef.current = startY;
      trackingRef.current = true;
    };

    const onTouchMove = (event: TouchEvent) => {
      if (!trackingRef.current || startYRef.current === null || window.scrollY > 0) return;

      const currentY = event.touches[0]?.clientY;
      if (currentY === undefined) return;

      const nextDistance = Math.max(0, Math.min(currentY - startYRef.current, MAX_DISTANCE));
      distanceRef.current = nextDistance;
      setDistance(nextDistance);
    };

    const finishGesture = () => {
      if (!trackingRef.current) return;

      const shouldRefresh = distanceRef.current >= TRIGGER_DISTANCE;
      trackingRef.current = false;
      startYRef.current = null;

      if (shouldRefresh) {
        setRefreshing(true);
        setDistance(TRIGGER_DISTANCE);
        window.setTimeout(() => window.location.reload(), 120);
        return;
      }

      distanceRef.current = 0;
      setDistance(0);
    };

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", finishGesture, { passive: true });
    window.addEventListener("touchcancel", finishGesture, { passive: true });

    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", finishGesture);
      window.removeEventListener("touchcancel", finishGesture);
    };
  }, []);

  const visible = distance > 0 || refreshing;
  const ready = distance >= TRIGGER_DISTANCE;

  return (
    <div
      aria-live="polite"
      aria-hidden={!visible}
      className={cn(
        "pointer-events-none fixed left-1/2 top-2 z-[60] flex -translate-x-1/2 items-center gap-2 rounded-full border border-slate-200 bg-white/95 px-3 py-2 text-xs font-semibold text-slate-700 shadow-lg backdrop-blur-md transition-opacity dark:border-slate-700 dark:bg-slate-900/95 dark:text-slate-200",
        visible ? "opacity-100" : "opacity-0",
      )}
      style={{ transform: `translate(-50%, ${Math.max(distance - 34, 0)}px)` }}
    >
      <RefreshCw className={cn("size-4 text-sky-600", refreshing && "animate-spin")} aria-hidden />
      <span>{refreshing ? "Aggiornamento…" : ready ? "Rilascia per aggiornare" : "Trascina per aggiornare"}</span>
    </div>
  );
}
