// Hand-written mirrors of the Pydantic models in backend/models/schemas.py.
// Keep the two in sync in the same edit.

export type RiskType =
  | "microbiologico"
  | "chimico"
  | "allergeni"
  | "fisico"
  | "etichettatura"
  | "altro";

export type Severity = "grave" | "attenzione" | "informativo";

export interface RecallLot {
  lot_code: string;
  expiration_date: string | null;
  notes: string | null;
}

export interface Recall {
  id: string;
  source: string;
  source_id: string;
  source_url: string | null;
  pdf_url: string | null;
  product_url: string | null;
  image_url: string | null;
  title: string;
  brand: string | null;
  product_name: string;
  category: string | null;
  ean: string | null;
  risk_type: RiskType;
  severity: Severity;
  risk_description: string | null;
  consumer_advice: string | null;
  osa: string | null;
  producer: string | null;
  plant_mark: string | null;
  plant: string | null;
  package_size: string | null;
  expiration_date: string | null;
  document_date: string | null;
  lots: RecallLot[];
  is_seafood: boolean;
  fao_area_code: string | null;
  scientific_name: string | null;
  production_method: string | null;
  published_at: string;
  content_hash: string;
  verified: boolean;
  is_demo: boolean;
  field_confidence: Record<string, number>;
  official_fields: Record<string, string>;
  retrieved_at: string;
}

export interface RecallStats {
  total: number;
  last_30_days: number;
  microbiologico: number;
  allergeni: number;
  chimico: number;
  fisico: number;
  seafood: number;
}

export type PantryStatus = "ok" | "controlla_lotto" | "richiamato" | "scaduto";

export interface PantryItemCreate {
  name: string;
  brand?: string | null;
  ean?: string | null;
  lot_code?: string | null;
  expiration_date?: string | null;
  purchase_date?: string | null;
  store?: string | null;
}

export interface PantryItem {
  id: string;
  name: string;
  brand: string | null;
  ean: string | null;
  lot_code: string | null;
  expiration_date: string | null;
  purchase_date: string | null;
  store: string | null;
  created_at: string;
  status: PantryStatus;
  status_label: string;
  match_confidence: number;
  matched_recall_id: string | null;
  matched_recall_title: string | null;
}

export interface FaoArea {
  id: string;
  code: string;
  name_it: string;
  name_en: string;
  parent_code: string | null;
  level: number;
  level_label: string;
  ocean: string | null;
  description: string | null;
  common_species: string[];
  centroid_lat: number | null;
  centroid_lon: number | null;
  source_name: string;
  source_url: string;
  source_record_id: string | null;
  retrieved_at: string | null;
  updated_at: string;
}

export interface FaoGeometry {
  code: string;
  geometry: GeoJSON.Geometry;
  source_name: string;
  source_url: string;
}

export interface FaoOverviewProps {
  code: string;
  name_it: string;
  level: number;
}
export type FaoOverview = GeoJSON.FeatureCollection<GeoJSON.Geometry, FaoOverviewProps>;

export interface EnvironmentMeasurement {
  id: string;
  fao_area_code: string;
  source: string;
  source_url: string;
  parameter: string;
  label_it: string;
  value: number | null;
  unit: string;
  reference_value: number | null;
  reference_note: string | null;
  sample_type: "water" | "sediment" | "biota";
  species: string | null;
  depth: number | null;
  latitude: number | null;
  longitude: number | null;
  measurement_date: string | null;
  quality_flag: string;
  is_demo: boolean;
  retrieved_at: string;
}

export interface EnvironmentSummary {
  fao_area_code: string;
  water: EnvironmentMeasurement[];
  sediment: EnvironmentMeasurement[];
  biota: EnvironmentMeasurement[];
  last_updated: string | null;
  sources: string[];
  note: string;
}

export interface AppNotification {
  id: string;
  type: "richiamo_prodotto" | "lotto_corrispondente" | "marca_seguita" | "zona_fao" | "ambientale";
  title: string;
  body: string;
  recall_id: string | null;
  read: boolean;
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  url: string;
  source_type: string;
  schedule: string;
  active: boolean;
  last_sync_at: string | null;
  last_successful_sync_at: string | null;
  last_error: string | null;
  record_count: number;
  pending_count: number;
  last_recheck_at: string | null;
}

export interface SyncResult {
  source_id: string;
  ok: boolean;
  message: string;
  fetched: number;
  inserted: number;
  updated: number;
  unchanged: number;
  failed: number;
}

export interface AdminSession {
  authenticated: boolean;
  user: {
    email: string;
    role: "admin";
  };
}

export interface AdapterStatus {
  name: string;
  configured: boolean;
  reason: string;
  docs_url: string;
}

export interface AdminOverview {
  recalls: number;
  recalls_to_verify: number;
  demo_recalls: number;
  pantry_items: number;
  notifications: number;
  fao_areas: number;
  measurements: number;
  environment_adapters: AdapterStatus[];
}
