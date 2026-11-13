import type { ExchangeRate, PriceObservation, Product } from "@/types"
import type { ManagedStore } from "@/types/store"
import type { StoreProduct } from "@/types/storeProduct"

export type MarketAlertKind = "price_up" | "price_down" | "new_minimum" | "fx_change" | "stale_price" | "stale_fx" | "extraction_failed" | "extraction_partial" | "extraction_success"
export type ResourceState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "available" | "empty"; data: T; error: null }
  | { status: "error"; data: null; error: string }

export type LoadedResource<T> = Exclude<ResourceState<T>, { status: "loading" }>
export function loadResource<T>(request: Promise<T>): Promise<LoadedResource<T>>
export function reachedRecordLimit(rows: unknown[], limit?: number): boolean
export interface MarketAlert {
  key: string
  kind: MarketAlertKind
  title: string
  detail: string
  storeName?: string
  productName?: string
  previousValue?: string
  currentValue?: string
  changePercent?: number
  previousAt?: string
  observedAt?: string
  source?: string
  sourceUrl?: string | null
}

export function deriveMarketAlerts(input: {
  observations: PriceObservation[]
  listings: StoreProduct[]
  products: Product[]
  stores: ManagedStore[]
  rates: ExchangeRate[]
  threshold: number
  categoryId: number | null
  storeId?: number | null
  now?: number
}): MarketAlert[]
