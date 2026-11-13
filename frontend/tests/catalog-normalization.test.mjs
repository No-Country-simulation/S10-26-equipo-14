import assert from "node:assert/strict"
import { after, test } from "node:test"
import React from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

const vite = await createServer({
  configFile: "vite.config.ts",
  appType: "custom",
  logLevel: "silent",
  server: { middlewareMode: true },
})
const { default: CatalogProductSummary, CatalogPresentation } = await vite.ssrLoadModule(
  "/src/components/catalog/CatalogProductSummary.tsx",
)
const { apiClient } = await vite.ssrLoadModule("/src/lib/api.ts")

after(async () => vite.close())

const product = (overrides = {}) => ({
  id: 1,
  name: "Pack de prueba",
  brand: null,
  model: null,
  description: null,
  barcode: null,
  category_id: null,
  package_quantity: "500.000000",
  package_unit: "ml",
  package_count: 6,
  normalized_quantity: "3000.000000",
  normalized_unit: "ml",
  latest_price: {
    amount: "1500.00",
    promotional_price: "1200.00",
    currency: "ARS",
    observed_at: "2026-11-10T12:00:00Z",
    store_id: 2,
    store_name: "Tienda de prueba",
    store_product_id: 3,
    source_url: null,
    is_available: true,
    normalized_quantity: "3000.000000",
    normalized_unit: "ml",
    normalized_price: "0.5",
    normalized_promotional_price: "0.4",
    normalization_unavailable_reason: null,
  },
  ...overrides,
})

test("renders source presentation, published price, and normalized prices", () => {
  const item = product()
  const presentation = renderToStaticMarkup(
    React.createElement(CatalogPresentation, { product: item }),
  )
  const price = renderToStaticMarkup(
    React.createElement(CatalogProductSummary, { product: item }),
  )

  assert.match(presentation, /6 × 500 ml/)
  assert.match(presentation, /3\.000 ml en total/)
  assert.match(price, /1\.500,00/)
  assert.match(price, /0,50.*\/ ml/)
  assert.match(price, /1\.200,00/)
  assert.match(price, /0,40.*\/ ml/)
})

test("labels absent package metadata and unavailable unit price", () => {
  const item = product({
    package_quantity: null,
    package_unit: null,
    package_count: null,
    normalized_quantity: null,
    normalized_unit: null,
    normalization_unavailable_reason: "missing_package_quantity",
    latest_price: {
      ...product().latest_price,
      normalized_quantity: null,
      normalized_unit: null,
      normalized_price: null,
      normalized_promotional_price: null,
      normalization_unavailable_reason: "missing_package_quantity",
    },
  })
  const presentation = renderToStaticMarkup(
    React.createElement(CatalogPresentation, { product: item }),
  )
  const price = renderToStaticMarkup(
    React.createElement(CatalogProductSummary, { product: item }),
  )

  assert.match(presentation, /Presentación no informada/)
  assert.match(price, /Faltan datos de presentación/)
  assert.match(price, /1\.500,00/)
})

test("labels demo source prices as synthetic and not current", () => {
  const item = product({
    latest_price: {
      ...product().latest_price,
      store_name: "DEMO PriceScope Tienda B",
    },
  })
  const price = renderToStaticMarkup(
    React.createElement(CatalogProductSummary, { product: item }),
  )

  assert.match(price, /Datos sintéticos de demostración; no son precios actuales/)
})

test("exchange-rate requests include the required rate type", async () => {
  const originalFetch = globalThis.fetch
  const requestedUrls = []
  globalThis.fetch = async (input) => {
    requestedUrls.push(String(input))
    return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } })
  }

  try {
    await apiClient.fetchExchangeRates({ limit: 10 })
    await apiClient.fetchExchangeRates({ rate_type: "blue", limit: 10 })
  } finally {
    globalThis.fetch = originalFetch
  }

  assert.equal(new URL(requestedUrls[0], "https://example.test").searchParams.get("rate_type"), "official")
  assert.equal(new URL(requestedUrls[1], "https://example.test").searchParams.get("rate_type"), "blue")
})

test("public catalogue requests only current verified listings", async () => {
  const originalFetch = globalThis.fetch
  let requestedUrl = ""
  globalThis.fetch = async (input) => {
    requestedUrl = String(input)
    return new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0, verified_only: true }), {
      status: 200, headers: { "Content-Type": "application/json" },
    })
  }
  try {
    await apiClient.fetchProductsWithPrices({ limit: 20, offset: 0, verified_only: true })
  } finally {
    globalThis.fetch = originalFetch
  }
  assert.equal(new URL(requestedUrl, "https://example.test").searchParams.get("verified_only"), "true")
})

test("older public management responses fail closed on missing coverage fields", async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify([{
    id: 2, name: "Frávega", base_url: "https://www.fravega.com", country: "AR", is_active: true,
    created_at: "2026-11-12T00:00:00Z", integration_status: "configuration_required",
    analyzer_key: null, analysis_message: null, analysis_candidates: [], last_analysis_at: null,
    currency: "ARS", interval_hours: 24, monitoring_enabled: false, category_ids: [],
    last_extraction_at: "2026-11-12T10:00:00Z", last_extraction_status: "SUCCESS",
  }]), { status: 200, headers: { "Content-Type": "application/json" } })
  try {
    const [store] = await apiClient.fetchManagedStores()
    assert.equal(store.last_extraction_status, "SUCCESS")
    assert.equal(store.is_operational, false)
    assert.equal(store.coverage_status, "connector_unverified")
    assert.match(store.extraction_disabled_reason, /no publica datos de cobertura verificables/)
  } finally {
    globalThis.fetch = originalFetch
  }
})
