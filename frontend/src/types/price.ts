/**
 * Interfaz PriceObservation — Modelo de dominio del backend.
 *
 * PENDIENTE DE CONFIRMAR con el backend (backend/app/models/price.py vacío).
 * Definición preliminar basada en docs/arquitectura.md.
 */
export interface PriceObservation {
  id: number
  product_id: number
  store_id: number
  amount: number
  currency: string
  observed_at: string // ISO 8601
}