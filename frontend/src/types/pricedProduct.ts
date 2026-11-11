import type { Product } from './product'

export interface LatestProductPrice {
  amount: string
  currency: string
  observed_at: string
  store_id: number
  store_name: string
  store_product_id: number
  source_url: string | null
  is_available: boolean | null
}

export interface PricedProduct extends Product {
  latest_price: LatestProductPrice | null
}

export interface PricedProductPage {
  items: PricedProduct[]
  total: number
  limit: number
  offset: number
}
