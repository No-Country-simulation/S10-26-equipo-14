/**
 * Interfaz Product — Modelo de dominio del backend.
 *
 * PENDIENTE DE CONFIRMAR con el backend (backend/app/models/product.py vacío).
 * Definición preliminar basada en docs/arquitectura.md.
 */
export interface Product {
  id: number
  store_id: number
  category_id: number | null
  name: string
  sku: string | null
  url: string | null
  is_active: boolean
}