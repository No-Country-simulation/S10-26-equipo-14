/** Canonical product shared across store listings. */
export interface Product {
  id: number
  name: string
  brand: string | null
  model: string | null
  description: string | null
  barcode: string | null
  category_id: number | null
}
