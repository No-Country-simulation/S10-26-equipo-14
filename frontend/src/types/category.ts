/**
 * Interfaz Category — Modelo de dominio del backend.
 *
 * PENDIENTE DE CONFIRMAR con el backend (backend/app/models/category.py vacío).
 * Definición preliminar basada en docs/arquitectura.md.
 */
export interface Category {
  id: number
  name: string
  slug: string
  description: string | null
}