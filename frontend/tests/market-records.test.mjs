import assert from "node:assert/strict"
import test from "node:test"

import { isSyntheticSource, summarizeStoreCoverage } from "../src/lib/marketRecords.js"

const now = Date.parse("2026-11-12T20:00:00Z")
const stores = [
  { id: 1, name: "Cetrogar", connector_available: false, connector_configured: false, last_extraction_status: "SUCCESS" },
  { id: 2, name: "Frávega", connector_available: true, connector_configured: false, last_extraction_status: null },
  { id: 3, name: "DEMO PriceScope Tienda A", connector_available: false, connector_configured: false, last_extraction_status: "SUCCESS" },
]
const listings = [
  { id: 10, store_id: 1, product_id: 5, product_name: "Café" },
  { id: 11, store_id: 2, product_id: 5, product_name: "Café" },
  { id: 12, store_id: 3, product_id: 99, product_name: "DEMO PriceScope Producto" },
]
const observations = [
  { id: 1, store_product_id: 10, amount: "100.00", currency: "ARS", is_available: true, observed_at: "2026-11-12T19:00:00Z" },
  { id: 2, store_product_id: 10, amount: "90.00", currency: "ARS", is_available: null, observed_at: "2026-11-10T19:00:00Z" },
  { id: 3, store_product_id: 11, amount: "110.00", currency: "ARS", is_available: false, observed_at: "2026-11-12T19:00:00Z" },
  { id: 4, store_product_id: 12, amount: "1.00", currency: "ARS", is_available: true, observed_at: "2026-11-12T19:00:00Z" },
]

test("store summary separates registered demos, real connector coverage, and successful runs", () => {
  const summary = summarizeStoreCoverage(stores, listings, observations, now)
  assert.equal(summary.registeredStoreCount, 3)
  assert.equal(summary.demoStoreCount, 1)
  assert.equal(summary.realStores.length, 2)
  assert.equal(summary.implementedConnectorCount, 1)
  assert.equal(summary.configuredConnectorCount, 0)
  assert.equal(summary.successfulExtractionStoreCount, 1)
})

test("price history keeps older real observations and excludes demo or unavailable rows", () => {
  const summary = summarizeStoreCoverage(stores, listings, observations, now)
  assert.deepEqual(summary.realObservations.map(({ observation }) => observation.id), [1, 2])
  assert.equal(summary.recentObservationCount, 1)
  assert.equal(summary.historicalObservationCount, 1)
  assert.equal(summary.storesWithRecentPrices, 1)
  assert.equal(summary.storesWithHistoricalPrices, 1)
  assert.equal(summary.realPricedProductCount, 1)
  assert.equal(summary.storePriceHistory.get(1).length, 2)
  assert.equal(summary.storePriceHistory.get(2).length, 0)
  assert.equal(summary.totalObservationRows, 4)
})

test("synthetic quote sources can be identified and kept out of public charts", () => {
  assert.equal(isSyntheticSource("DEMO PriceScope"), true)
  assert.equal(isSyntheticSource("synthetic fixture"), true)
  assert.equal(isSyntheticSource("Banco central"), false)
})
