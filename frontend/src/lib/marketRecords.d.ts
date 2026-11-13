import type { PriceObservation } from "@/types/price"
import type { ManagedStore } from "@/types/store"
import type { StoreProduct } from "@/types/storeProduct"

export interface StoreHistoryRow {
  observation: PriceObservation
  listing: StoreProduct
}

export interface StoreCoverageSummary {
  registeredStoreCount: number
  demoStoreCount: number
  realStores: ManagedStore[]
  realListings: StoreProduct[]
  realObservations: StoreHistoryRow[]
  totalObservationRows: number
  implementedConnectorCount: number
  configuredConnectorCount: number
  successfulExtractionStoreCount: number
  storesWithRecentPrices: number
  recentObservationCount: number
  historicalObservationCount: number
  storesWithHistoricalPrices: number
  realPricedProductCount: number
  storePriceHistory: Map<number, StoreHistoryRow[]>
}

export function isDemoName(value: string | null | undefined): boolean
export function isSyntheticSource(source: string | null | undefined): boolean
export function summarizeStoreCoverage(
  stores: ManagedStore[],
  listings: StoreProduct[],
  observations: PriceObservation[],
  now?: number,
): StoreCoverageSummary
