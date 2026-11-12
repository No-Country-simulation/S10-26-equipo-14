/** Canonical product shared across store listings. */
export interface Product {
  id: number
  name: string
  brand: string | null
  model: string | null
  description: string | null
  barcode: string | null
  category_id: number | null
  /** Original presentation fields; optional while reading older API deployments. */
  package_quantity?: string | null
  package_unit?: string | null
  package_count?: number | null
  normalized_quantity?: string | null
  normalized_unit?: string | null
  normalization_unavailable_reason?: string | null
}
