/**
 * Interfaz Store — Modelo de persistencia del backend.
 *
 * Basado en backend/app/models/store.py (implementado).
 * Campos alineados con el modelo SQLAlchemy de tiendas.
 */
export interface Store {
  id: number
  name: string
  base_url: string
  country: string | null
  is_active: boolean
  created_at: string // ISO 8601; PostgreSQL TIMESTAMPTZ
}

export type StoreIntegrationStatus =
  | 'pending'
  | 'analyzing'
  | 'configuration_required'
  | 'active'
  | 'error'

export interface StoreCategoryCandidate {
  name: string
  source_url: string
  category_id: number | null
}

export interface ManagedStore extends Store {
  integration_status: StoreIntegrationStatus
  analyzer_key: string | null
  analysis_message: string | null
  analysis_candidates: StoreCategoryCandidate[]
  last_analysis_at: string | null
  currency: string
  interval_hours: number
  monitoring_enabled: boolean
  category_ids: number[]
  last_extraction_at: string | null
  last_extraction_status: string | null
}

export interface CreateStoreInput {
  name: string
  base_url: string
  country: string
  currency: string
}

export interface StoreMonitoringInput {
  category_ids: number[]
  currency: string
  interval_hours: number
  enabled: boolean
}
