/** Store-specific publication, separate from its optional canonical Product. */
export interface StoreProduct {
  id: number
  store_id: number
  product_id: number | null
  category_id: number | null
  external_id: string | null
  product_url: string
  product_name: string
  currency: string
}
