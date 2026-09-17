import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { FaoOverview, FaoOverviewProps } from "@/types/api";

interface Props {
  overview: FaoOverview | undefined; // thinned outlines of the areas at the current browsing level
  selectedCode: string;
  selectedGeometry: GeoJSON.Geometry | undefined; // official full-resolution geometry of the selection
  onSelectZone: (code: string) => void;
}

// Interactive FAO map: OpenStreetMap tiles and official FAO (CWP) geometries.
export default function FaoMap({
  overview,
  selectedCode,
  selectedGeometry,
  onSelectZone,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const zonesLayer = useRef<L.LayerGroup>(L.layerGroup());
  const selectedLayer = useRef<L.LayerGroup>(L.layerGroup());

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { center: [30, 10], zoom: 2, scrollWheelZoom: false, worldCopyJump: true });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · Zone: FAO CWP',
      maxZoom: 12,
    }).addTo(map);
    zonesLayer.current.addTo(map);
    selectedLayer.current.addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // overview outlines (siblings / children of the browsing level)
  useEffect(() => {
    const layer = zonesLayer.current;
    layer.clearLayers();
    if (!overview) return;
    L.geoJSON<FaoOverviewProps>(overview, {
      style: (f) => ({
        color: f?.properties.code === selectedCode ? "#0284C7" : "#475569",
        weight: 1,
        fillColor: "#94A3B8",
        fillOpacity: 0.06,
        dashArray: "4 4",
      }),
      onEachFeature: (f, l) => {
        l.bindTooltip(`FAO ${f.properties.code} · ${f.properties.name_it}`, { sticky: true });
        l.on("click", () => onSelectZone(f.properties.code));
      },
    }).addTo(layer);
  }, [overview, selectedCode, onSelectZone]);

  // selected area, official full geometry, highlighted + fitted
  useEffect(() => {
    const map = mapRef.current;
    const layer = selectedLayer.current;
    layer.clearLayers();
    if (!map || !selectedGeometry) return;
    const g = L.geoJSON(selectedGeometry, {
      style: { color: "#0284C7", weight: 3, fillColor: "#0284C7", fillOpacity: 0.22 },
    }).addTo(layer);
    const bounds = g.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 7 });
  }, [selectedGeometry]);

  return (
    <div
      ref={containerRef}
      data-testid="fao-map"
      role="region"
      aria-label="Mappa interattiva delle zone FAO"
      className="h-80 w-full overflow-hidden rounded-2xl border border-sky-200 dark:border-sky-900 md:h-[440px]"
    />
  );
}
