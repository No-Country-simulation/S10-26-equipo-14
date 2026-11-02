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
