const DEMO_PREFIX = "DEMO PriceScope "
const SYNTHETIC_SOURCE = /demo|synthetic|sint[eé]tic/i

export function isDemoName(value) {
  return typeof value === "string" && value.startsWith(DEMO_PREFIX)
}

export function isSyntheticSource(source) {
  return typeof source === "string" && SYNTHETIC_SOURCE.test(source)
}

export function summarizeStoreCoverage(stores, listings, observations, now = Date.now()) {
  const realStores = stores.filter((store) => !isDemoName(store.name))
  const realStoreIds = new Set(realStores.map((store) => store.id))
  const realListings = listings.filter((listing) =>
    realStoreIds.has(listing.store_id) && !isDemoName(listing.product_name),
  )
  const listingsById = new Map(realListings.map((listing) => [listing.id, listing]))
  const realObservations = observations
    .filter((observation) => observation.is_available !== false && listingsById.has(observation.store_product_id))
    .map((observation) => ({ observation, listing: listingsById.get(observation.store_product_id) }))
    .sort((left, right) => Date.parse(right.observation.observed_at) - Date.parse(left.observation.observed_at))
  const cutoff = now - 48 * 60 * 60 * 1000
  const isRecent = ({ observation }) => {
    const timestamp = Date.parse(observation.observed_at)
    return Number.isFinite(timestamp) && timestamp >= cutoff && timestamp <= now
  }
  const recentObservations = realObservations.filter(isRecent)
  const historicalObservations = realObservations.filter(({ observation }) => {
    const timestamp = Date.parse(observation.observed_at)
    return Number.isFinite(timestamp) && timestamp < cutoff
  })
  const rowsByStore = (rows) => new Set(rows.map(({ listing }) => listing.store_id))
  const storePriceHistory = new Map(realStores.map((store) => [
    store.id,
    realObservations.filter(({ listing }) => listing.store_id === store.id),
  ]))
  const realPricedProductIds = new Set(realObservations
    .map(({ listing }) => listing.product_id)
    .filter((productId) => productId !== null))

  return {
    registeredStoreCount: stores.length,
    demoStoreCount: stores.length - realStores.length,
    realStores,
    realListings,
    realObservations,
    totalObservationRows: observations.length,
    implementedConnectorCount: realStores.filter((store) => store.connector_available).length,
    configuredConnectorCount: realStores.filter((store) => store.connector_configured).length,
    successfulExtractionStoreCount: realStores.filter((store) => store.last_extraction_status === "SUCCESS").length,
    storesWithRecentPrices: rowsByStore(recentObservations).size,
    recentObservationCount: recentObservations.length,
    historicalObservationCount: historicalObservations.length,
    storesWithHistoricalPrices: rowsByStore(historicalObservations).size,
    realPricedProductCount: realPricedProductIds.size,
    storePriceHistory,
  }
}
