import assert from "node:assert/strict"
import test from "node:test"

import { deriveMarketAlerts, loadResource, reachedRecordLimit } from "../src/lib/marketAlerts.js"

const now = Date.parse("2026-11-12T12:00:00Z")

test("independent resource requests preserve successful results when another API request fails", async () => {
  const [products, observations] = await Promise.all([
    loadResource(Promise.resolve([{ id: 1 }])),
    loadResource(Promise.reject(new Error("API no disponible"))),
  ])
  assert.equal(products.status, "available")
  assert.deepEqual(products.data, [{ id: 1 }])
  assert.equal(observations.status, "error")
  assert.equal(observations.error, "API no disponible")
})

test("empty API responses stay distinct from errors and record cap is explicit", async () => {
  const empty = await loadResource(Promise.resolve([]))
  const nonempty = await loadResource(Promise.resolve([1, 2]))
  assert.equal(empty.status, "empty")
  assert.deepEqual(empty.data, [])
  assert.equal(nonempty.status, "available")
  assert.equal(reachedRecordLimit(Array.from({ length: 1000 }), 1000), true)
  assert.equal(reachedRecordLimit(Array.from({ length: 999 }), 1000), false)
})
const base = {
  products: [{ id: 1, name: "Producto real", category_id: 4 }],
  listings: [{ id: 10, store_id: 7, product_id: 1, category_id: 4, product_name: "Producto real", product_url: "https://shop.test/item" }],
  stores: [{ id: 7, name: "Comercio real", is_active: true, last_extraction_status: null, last_extraction_at: null }],
  observations: [], rates: [], threshold: 5, categoryId: null, now,
}

function observation(id, amount, day, options = {}) {
  return {
    id, store_product_id: 10, amount: String(amount), promotional_price: null,
    currency: "ARS", observed_at: `${day}T10:00:00Z`, source_url: "https://shop.test/item",
    is_available: true, ...options,
  }
}

test("price alerts compare consecutive same-listing observations and deduplicate event keys", () => {
  const alerts = deriveMarketAlerts({ ...base, observations: [
    observation(1, 100, "2026-11-10"), observation(2, 110, "2026-11-11"),
  ] })
  assert.deepEqual(alerts.map((alert) => alert.kind), ["price_up"])
  assert.equal(alerts[0].changePercent, 10)
  assert.equal(alerts[0].previousValue, "ARS 100")
  assert.equal(alerts[0].currentValue, "ARS 110")
})

test("a single observation is insufficient and unavailable observations are excluded", () => {
  const single = deriveMarketAlerts({ ...base, observations: [observation(1, 100, "2026-11-12")] })
  const unavailable = deriveMarketAlerts({ ...base, observations: [
    observation(1, 100, "2026-11-12"), observation(2, 200, "2026-11-12", { is_available: false }),
  ] })
  assert.deepEqual(single, [])
  assert.deepEqual(unavailable, [])
})

test("stale data alert can be generated from one real observation", () => {
  const stale = deriveMarketAlerts({ ...base, now, observations: [
    observation(1, 100, "2026-11-09"),
  ] })
  assert.deepEqual(stale.map((alert) => alert.kind), ["stale_price"])
})

test("price decreases and new period minimums are separate source-backed signals", () => {
  const alerts = deriveMarketAlerts({ ...base, observations: [
    observation(1, 100, "2026-11-10"), observation(2, 90, "2026-11-11"),
  ] })
  assert.deepEqual(new Set(alerts.map((alert) => alert.kind)), new Set(["price_down", "new_minimum"]))
})

test("demo products and quotes are excluded; latest extraction status is reported", () => {
  const input = {
    ...base,
    stores: [{ ...base.stores[0], last_extraction_status: "BLOCKED", last_extraction_at: "2026-11-12T11:00:00Z" }],
    observations: [observation(1, 100, "2026-11-10"), observation(2, 110, "2026-11-11")],
    rates: [
      { id: 1, source: "MonedAPI", rate_type: "official", rate_side: "reference", base_currency: "USD", quote_currency: "ARS", rate: "1000", observed_at: "2026-11-10T10:00:00Z" },
      { id: 2, source: "MonedAPI", rate_type: "official", rate_side: "reference", base_currency: "USD", quote_currency: "ARS", rate: "1100", observed_at: "2026-11-11T10:00:00Z" },
      { id: 3, source: "DEMO synthetic", rate_type: "parallel", rate_side: "sell", base_currency: "USD", quote_currency: "ARS", rate: "2000", observed_at: "2026-11-11T10:00:00Z" },
    ],
  }
  const alerts = deriveMarketAlerts(input)
  assert.equal(alerts.filter((alert) => alert.kind === "fx_change").length, 1)
  assert.equal(alerts.filter((alert) => alert.kind === "extraction_failed").length, 1)
  assert.equal(alerts.some((alert) => alert.source?.includes("DEMO")), false)
})

test("latest partial extraction is represented as partial, not as a previous success", () => {
  const alerts = deriveMarketAlerts({ ...base, stores: [{
    ...base.stores[0], last_extraction_status: "PARTIAL_SUCCESS", last_extraction_at: "2026-11-12T11:00:00Z",
  }] })
  assert.equal(alerts.length, 1)
  assert.equal(alerts[0].kind, "extraction_partial")
})
