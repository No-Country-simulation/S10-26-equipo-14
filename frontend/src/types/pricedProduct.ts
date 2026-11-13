import type { Product } from './product'

export interface LatestProductPrice {
  amount: string
  promotional_price?: string | null
  currency: string
  observed_at: string
  store_id: number
  store_name: string
  store_product_id: number
  source_url: string | null
  is_available: boolean | null
  normalized_quantity?: string | null
  normalized_unit?: string | null
  normalized_price?: string | null
  normalized_promotional_price?: string | null
  normalization_unavailable_reason?: string | null
  promotional_normalization_unavailable_reason?: string | null
}

export interface PricedProduct extends Product {
  latest_price: LatestProductPrice | null
}

export interface PricedProductPage {
  items: PricedProduct[]
  total: number
  limit: number
  offset: number
  verified_only?: boolean
}
