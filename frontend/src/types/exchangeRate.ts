/**
 * Interfaz ExchangeRate — Modelo de dominio del backend.
 *
 * PENDIENTE DE CONFIRMAR con el backend (backend/app/models/exchange_rate.py vacío).
 * Definición preliminar basada en docs/arquitectura.md.
 */
export interface ExchangeRate {
  id: number
  pair: string // ej. "USD/ARS"
  rate: number
  source: string
  recorded_at: string // ISO 8601
}