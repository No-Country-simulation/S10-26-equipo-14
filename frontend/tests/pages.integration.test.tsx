// @vitest-environment jsdom
import React from "react"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({
  fetchProductsWithPrices: vi.fn(),
  fetchCategories: vi.fn(),
  fetchStores: vi.fn(),
  fetchStoreProducts: vi.fn(),
  fetchPriceObservations: vi.fn(),
  fetchExchangeRates: vi.fn(),
  fetchComparisons: vi.fn(),
  fetchInflation: vi.fn(),
  fetchShrinkflation: vi.fn(),
}))

vi.mock("@/lib/api", () => ({
  apiClient: api,
  ApiError: class ApiError extends Error {},
}))

vi.mock("@/components/charts/DualAxisTimeSeriesChart", () => ({
  default: () => <div data-testid="price-rate-chart" />,
}))

import CatalogoPage from "@/pages/CatalogoPage"
import DivisasPage from "@/pages/DivisasPage"
import ComparativasPage from "@/pages/ComparativasPage"

const productWithoutPrice = {
  id: 40,
  name: "Producto real todavía sin precio",
  brand: null,
  model: null,
  description: null,
  barcode: null,
  category_id: null,
  package_quantity: null,
  package_unit: null,
  package_count: null,
  normalized_quantity: null,
  normalized_unit: null,
  normalization_unavailable_reason: "missing_package_quantity",
  latest_price: null,
}

const productWithPrice = {
  ...productWithoutPrice,
  id: 41,
  name: "Snack Tasty Bite Carne Pedigree 40 Gr.",
  latest_price: {
    amount: "925.00",
    promotional_price: null,
    currency: "ARS",
    observed_at: "2026-11-13T10:00:00Z",
    store_id: 6,
    store_name: "Día Online",
    store_product_id: 60,
    source_url: "https://diaonline.supermercadosdia.com.ar/snack-tasty-bite-carne-pedigree-40-gr-314778/p",
    is_available: true,
    normalized_quantity: null,
    normalized_unit: null,
    normalized_price: null,
    normalized_promotional_price: null,
    normalization_unavailable_reason: "missing_package_quantity",
    promotional_normalization_unavailable_reason: null,
  },
}

const categories = [{ id: 4, name: "Tecnología y electrónica", slug: "tecnologia" }]
const stores = [{ id: 6, name: "Día Online", base_url: "https://diaonline.supermercadosdia.com.ar", country: "AR", is_active: true, created_at: "2026-11-12T00:00:00Z" }]
const listing = { id: 60, store_id: 6, product_id: 41, category_id: null, external_id: "00314778", product_url: productWithPrice.latest_price.source_url, product_name: productWithPrice.name, currency: "ARS" }
const observations = [
  { id: 200, store_product_id: 60, amount: "925.00", promotional_price: null, currency: "ARS", source_url: listing.product_url, is_available: true, observed_at: "2026-11-12T10:00:00Z" },
  { id: 201, store_product_id: 60, amount: "925.00", promotional_price: null, currency: "ARS", source_url: listing.product_url, is_available: true, observed_at: "2026-11-13T10:00:00Z" },
]
const rates = [
  { id: 300, source: "BCRA", rate_type: "official", rate_side: "reference", base_currency: "USD", quote_currency: "ARS", rate: "1500.00", observed_at: "2026-11-12T10:00:00Z" },
  { id: 301, source: "BCRA", rate_type: "official", rate_side: "reference", base_currency: "USD", quote_currency: "ARS", rate: "1500.00", observed_at: "2026-11-13T10:00:00Z" },
  { id: 302, source: "DolarAPI", rate_type: "parallel", rate_side: "sell", base_currency: "USD", quote_currency: "ARS", rate: "1550.00", observed_at: "2026-11-12T10:00:00Z" },
  { id: 303, source: "DolarAPI", rate_type: "parallel", rate_side: "sell", base_currency: "USD", quote_currency: "ARS", rate: "1550.00", observed_at: "2026-11-13T10:00:00Z" },
]

function renderInRouter(element: React.ReactNode) {
  return render(<MemoryRouter initialEntries={["/catalogo"]}>{element}</MemoryRouter>)
}

function configureSuccessfulPageApis() {
  api.fetchProductsWithPrices.mockResolvedValue({ items: [productWithoutPrice, productWithPrice], total: 2, limit: 20, offset: 0, verified_only: false })
  api.fetchCategories.mockResolvedValue(categories)
  api.fetchStores.mockResolvedValue(stores)
  api.fetchStoreProducts.mockResolvedValue([listing])
  api.fetchPriceObservations.mockResolvedValue(observations)
  api.fetchExchangeRates.mockImplementation((params: { rate_type?: string }) => Promise.resolve(rates.filter((row) => row.rate_type === params.rate_type)))
  api.fetchComparisons.mockResolvedValue([{ product_id: 41, product_name: productWithPrice.name, category_id: null, currency: "ARS", spread_amount: "0.00", spread_percent: "0", prices: [] }])
  api.fetchInflation.mockResolvedValue({
    status: "available", message: null, start: "2026-11-12T00:00:00Z", end: "2026-11-13T23:59:59Z", method: "same-listing endpoints",
    currencies: [{ currency: "ARS", status: "available", inflation_percent: "0", fx_rate_type: "official", fx_variation_percent: "0", price_minus_fx_percentage_points: "0", fx_status: "available", products_count: 1, listings_count: 1 }],
    categories: [],
    products: [{ product_id: 41, product_name: productWithPrice.name, category_id: null, currency: "ARS", status: "available", inflation_percent: "0", listings_count: 1, listings: [{ store_product_id: 60, initial_price: "925.00", final_price: "925.00", initial_observed_at: observations[0].observed_at, final_observed_at: observations[1].observed_at }] }],
  })
  api.fetchShrinkflation.mockResolvedValue([])
}

beforeEach(() => {
  vi.clearAllMocks()
  configureSuccessfulPageApis()
})

afterEach(() => cleanup())

describe("Catálogo, Divisas y Comparativas contra el contrato de la API", () => {
  it("muestra productos canónicos con y sin precio y solicita el catálogo sin filtro Frávega", async () => {
    renderInRouter(<CatalogoPage />)

    expect(await screen.findByText(productWithoutPrice.name)).toBeTruthy()
    expect(screen.getByText("Sin observaciones de precio")).toBeTruthy()
    expect(screen.getByText(productWithPrice.name)).toBeTruthy()
    expect(screen.getByText(/925,00/)).toBeTruthy()
    await waitFor(() => expect(api.fetchProductsWithPrices).toHaveBeenCalled())
    expect(api.fetchProductsWithPrices.mock.calls[0]?.[0]?.verified_only).toBeUndefined()
  })

  it("resuelve Divisas con series persistidas y muestra las cotizaciones", async () => {
    renderInRouter(<DivisasPage />)

    expect(await screen.findByText(/USD\/ARS actual: 1500.00/)).toBeTruthy()
    expect(screen.getByText("Registros ARS: 2")).toBeTruthy()
    expect(screen.getByTestId("price-rate-chart")).toBeTruthy()
  })

  it("sale de carga en Divisas y ofrece reintento cuando falla un endpoint", async () => {
    api.fetchPriceObservations.mockRejectedValue(new Error("API temporalmente no disponible"))
    renderInRouter(<DivisasPage />)

    expect(await screen.findByRole("alert")).toBeTruthy()
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeTruthy()
    expect(screen.queryByText("Cargando series de la API…")).toBeNull()
  })

  it("muestra 0% cuando las observaciones en dos fechas y la serie FX confirman valor constante", async () => {
    renderInRouter(<ComparativasPage />)

    expect((await screen.findAllByText("0%")).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/Variación por producto/)).toBeTruthy()
    expect(screen.getByText(/925.00/)).toBeTruthy()
  })

  it("explica datos insuficientes en Comparativas sin presentarlos como 0%", async () => {
    api.fetchInflation.mockResolvedValue({
      status: "insufficient_data", message: "Se necesitan observaciones en dos fechas distintas.",
      start: "2026-11-12T00:00:00Z", end: "2026-11-13T23:59:59Z", method: "same-listing endpoints",
      currencies: [], categories: [], products: [],
    })
    renderInRouter(<ComparativasPage />)

    expect(await screen.findByText(/Se necesitan observaciones en dos fechas distintas/)).toBeTruthy()
    expect(screen.queryByText("0%")).toBeNull()
  })
})
