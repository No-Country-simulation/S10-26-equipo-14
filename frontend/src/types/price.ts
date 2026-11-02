/** Pydantic serializes Decimal as a JSON string to preserve precision. */
export type DecimalString = string

/** Historical price capture belonging to one store listing. */
export interface PriceObservation {
  id: number
  store_product_id: number
  amount: DecimalString
  promotional_price: DecimalString | null
  currency: string
  source_url: string | null
  is_available: boolean | null
  observed_at: string
}
