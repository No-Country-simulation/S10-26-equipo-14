import type { Category, Product } from "@/types"
import type { CreateStoreInput, ManagedStore, StoreMonitoringInput } from "@/types/store"
import type { Store, PriceObservation, ExchangeRate } from "@/types"
import type { ExtractionRun, PricedProduct, PricedProductPage } from "@/types"

/** Backend configurable; Vite proxy local en desarrollo y API desplegada en producción. */
const configuredBase = import.meta.env.VITE_API_URL?.trim()
const API_BASE = import.meta.env.DEV
  ? ""
  : (configuredBase || "https://pricescope-api.onrender.com")
    .replace(/\/$/, "")
    .replace(/\/api$/, "")

export class ApiError extends Error {
  public readonly status?: number

  constructor(
    message: string,
    status?: number
  ) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string"
}

function isOptionalNullableString(value: Record<string, unknown>, key: string): boolean {
  return !(key in value) || isNullableString(value[key])
}

function isOptionalNullableDecimal(value: Record<string, unknown>, key: string): boolean {
  return !(key in value) || value[key] === null || isDecimal(value[key])
}

function isProduct(value: unknown): value is Product {
  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    typeof value.name === "string" &&
    isNullableString(value.brand) &&
    isNullableString(value.model) &&
    isNullableString(value.description) &&
    isNullableString(value.barcode) &&
    (value.category_id === null || Number.isInteger(value.category_id)) &&
    isOptionalNullableDecimal(value, "package_quantity") &&
    isOptionalNullableString(value, "package_unit") &&
    (!("package_count" in value) || value.package_count === null || Number.isInteger(value.package_count)) &&
    isOptionalNullableDecimal(value, "normalized_quantity") &&
    isOptionalNullableString(value, "normalized_unit") &&
    isOptionalNullableString(value, "normalization_unavailable_reason")
  )
}

function isPricedProduct(value: unknown): value is PricedProduct {
  if (!isProduct(value) || !isRecord(value)) return false
  const price = value.latest_price
  return price === null || (
    isRecord(price) && typeof price.amount === "string" && Number.isFinite(Number(price.amount)) &&
    isOptionalNullableDecimal(price, "promotional_price") &&
    typeof price.currency === "string" && typeof price.observed_at === "string" &&
    Number.isInteger(price.store_id) && typeof price.store_name === "string" &&
    Number.isInteger(price.store_product_id) && isNullableString(price.source_url) &&
    (price.is_available === null || typeof price.is_available === "boolean") &&
    isOptionalNullableDecimal(price, "normalized_quantity") &&
    isOptionalNullableString(price, "normalized_unit") &&
    isOptionalNullableDecimal(price, "normalized_price") &&
    isOptionalNullableDecimal(price, "normalized_promotional_price") &&
    isOptionalNullableString(price, "normalization_unavailable_reason") &&
    isOptionalNullableString(price, "promotional_normalization_unavailable_reason")
  )
}

function isExtractionRun(value: unknown): value is ExtractionRun {
  return isRecord(value) && Number.isInteger(value.run_id) && Number.isInteger(value.store_id) &&
    typeof value.store_name === "string" && typeof value.source === "string" &&
    typeof value.status === "string" && typeof value.started_at === "string" &&
    (value.finished_at === null || typeof value.finished_at === "string") &&
    Number.isInteger(value.records_seen) && Number.isInteger(value.observations_created) &&
    isNullableString(value.error_summary)
}

function isCategory(value: unknown): value is Category {
  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    typeof value.name === "string" &&
    typeof value.slug === "string"
  )
}

const ADMIN_TOKEN_STORAGE_KEY = "pricescope.adminToken"
let adminApiToken: string | null = null

export function setAdminApiToken(token: string | null) {
  adminApiToken = token?.trim() || null
  if (typeof window !== "undefined") {
    if (adminApiToken) window.sessionStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, adminApiToken)
    else window.sessionStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
  }
}

function getAdminApiToken(): string | null {
  if (adminApiToken) return adminApiToken
  if (typeof window === "undefined") return null
  return window.sessionStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)
}

export function hasAdminApiToken(): boolean {
  return Boolean(getAdminApiToken())
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
        ...((init?.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase()) && getAdminApiToken())
          ? { "X-Admin-Token": getAdminApiToken() as string }
          : {}),
      },
    })
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error
    throw new ApiError(
      "No se pudo conectar con PriceScope API. Comprueba la conexión y la configuración CORS del backend."
    )
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => ({}))
    const detail = isRecord(body) && typeof body.detail === "string" ? body.detail : null
    throw new ApiError(detail ?? `Error ${response.status} al consultar ${path}`, response.status)
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new ApiError(`PriceScope API devolvió una respuesta JSON inválida para ${path}.`, response.status)
  }
}

export interface PaginatedProducts {
  items: Product[]
  total: number
  limit: number
  offset: number
}

export interface PriceComparison {
  product_id: number
  product_name: string
  category_id: number | null
  currency: string
  spread_amount: string
  spread_percent: string | null
  prices: Array<{
    store_id: number
    store_name: string
    store_product_id: number
    amount: string
    promotional_price: string | null
    effective_price: string
    currency: string
    observed_at: string
    source_url: string | null
    is_available: boolean | null
  }>
}

export interface PriceAlert {
  alert_type: "price_spike" | "price_increase_over_currency"
  product_id: number
  product_name: string
  store_id: number
  store_name: string
  store_product_id: number
  currency: string
  previous_price: string
  latest_price: string
  price_change_percent: string
  exchange_rate_type: "official" | "parallel" | null
  exchange_rate_change_percent: string | null
  previous_observed_at: string
  observed_at: string
  source_url: string | null
}

export interface InflationResult {
  status: "available" | "insufficient_data"
  message: string | null
  start: string
  end: string
  method: string
  currencies: Array<{
    currency: string
    status: "available"
    inflation_percent: string
    fx_rate_type: string | null
    fx_variation_percent: string | null
    price_minus_fx_percentage_points: string | null
    fx_status: string
    products_count: number
    listings_count: number
  }>
  categories: Array<{ category_id: number | null; currency: string; status: string; inflation_percent: string; products_count: number }>
  products: Array<{ product_id: number; product_name: string; category_id: number | null; currency: string; status: string; inflation_percent: string; listings_count: number; listings: Array<{ store_product_id: number; initial_price: string; final_price: string; initial_observed_at: string; final_observed_at: string }> }>
}

export interface ShrinkflationSignal {
  status: "confirmed" | "possible"
  product_id: number
  product_name: string
  store_id: number
  store_name: string
  store_product_id: number
  currency: string
  unit: string
  previous_quantity: string
  latest_quantity: string
  previous_price: string
  latest_price: string
  previous_unit_price: string
  latest_unit_price: string
  unit_price_change_percent: string
  previous_observed_at: string
  observed_at: string
  source_url: string | null
}

export interface ApiClient {
  fetchStores: (signal?: AbortSignal) => Promise<Store[]>
  fetchProducts: (
    params?: {
      category_id?: number | null
      search?: string
      limit?: number
      offset?: number
    },
    signal?: AbortSignal
  ) => Promise<PaginatedProducts>
  fetchProductsWithPrices: (
    params?: {
      category_id?: number | null
      search?: string
      start?: string
      end?: string
      limit?: number
      offset?: number
    },
    signal?: AbortSignal,
  ) => Promise<PricedProductPage>
  fetchCategories: (signal?: AbortSignal) => Promise<Category[]>
  fetchPriceObservations: (params?: {
    store_product_id?: number
    store_id?: number
    category_id?: number
    start?: string
    end?: string
    search?: string
    limit?: number
  }, signal?: AbortSignal) => Promise<PriceObservation[]>
  fetchExchangeRates: (params?: {
    rate_type?: string
    start?: string
    end?: string
    limit?: number
  }, signal?: AbortSignal) => Promise<ExchangeRate[]>
  fetchComparisons: (params?: { category_id?: number; store_id?: number; start?: string; end?: string; limit?: number }, signal?: AbortSignal) => Promise<PriceComparison[]>
  fetchAlerts: (params?: { category_id?: number; store_id?: number; start?: string; end?: string; rate_type?: "official" | "parallel"; spike_percent?: number; limit?: number }, signal?: AbortSignal) => Promise<PriceAlert[]>
  fetchInflation: (params: { category_id?: number; store_id?: number; product_id?: number; start: string; end: string; rate_type?: "official" | "parallel" }, signal?: AbortSignal) => Promise<InflationResult>
  fetchShrinkflation: (params?: { category_id?: number; store_id?: number; product_id?: number; start?: string; end?: string; limit?: number }, signal?: AbortSignal) => Promise<ShrinkflationSignal[]>
  fetchManagedStores: (signal?: AbortSignal) => Promise<ManagedStore[]>
  verifyAdminToken: (token: string) => Promise<boolean>
  createStore: (input: CreateStoreInput) => Promise<ManagedStore>
  analyzeStore: (storeId: number) => Promise<ManagedStore>
  saveStoreMonitoring: (storeId: number, input: StoreMonitoringInput) => Promise<ManagedStore>
  extractStore: (storeId: number) => Promise<ExtractionRun>
  fetchStoreExtractions: (storeId: number, limit?: number, signal?: AbortSignal) => Promise<ExtractionRun[]>
}

const integrationStatuses = new Set([
  "pending", "analyzing", "configuration_required", "active", "error",
])

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isInteger(value))
}

function isManagedStore(value: unknown): value is ManagedStore {
  return (
    isRecord(value) &&
    Number.isInteger(value.id) &&
    typeof value.name === "string" &&
    typeof value.base_url === "string" &&
    isNullableString(value.country) &&
    typeof value.is_active === "boolean" &&
    typeof value.created_at === "string" &&
    typeof value.integration_status === "string" &&
    integrationStatuses.has(value.integration_status) &&
    isNullableString(value.analyzer_key) &&
    isNullableString(value.analysis_message) &&
    Array.isArray(value.analysis_candidates) &&
    value.analysis_candidates.every((candidate) =>
      isRecord(candidate) &&
      typeof candidate.name === "string" &&
      typeof candidate.source_url === "string" &&
      isNullableNumber(candidate.category_id),
    ) &&
    (value.last_analysis_at === null || typeof value.last_analysis_at === "string") &&
    typeof value.currency === "string" &&
    Number.isInteger(value.interval_hours) &&
    typeof value.monitoring_enabled === "boolean" &&
    Array.isArray(value.category_ids) &&
    value.category_ids.every((categoryId) => Number.isInteger(categoryId)) &&
    (value.last_extraction_at === null || typeof value.last_extraction_at === "string") &&
    (value.last_extraction_status === null || typeof value.last_extraction_status === "string")
  )
}

function requireManagedStore(value: unknown): ManagedStore {
  if (!isManagedStore(value)) {
    throw new ApiError("PriceScope API devolvió una respuesta de gestión de tiendas inesperada.")
  }
  return value
}

function isStore(value: unknown): value is Store {
  return (
    isRecord(value) && Number.isInteger(value.id) && typeof value.name === "string" &&
    typeof value.base_url === "string" && isNullableString(value.country) &&
    typeof value.is_active === "boolean" && typeof value.created_at === "string"
  )
}

function isDecimal(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(Number(value))
}

function isPriceObservation(value: unknown): value is PriceObservation {
  return (
    isRecord(value) && Number.isInteger(value.id) && Number.isInteger(value.store_product_id) &&
    isDecimal(value.amount) && (value.promotional_price === null || isDecimal(value.promotional_price)) &&
    typeof value.currency === "string" && isNullableString(value.source_url) &&
    (value.is_available === null || typeof value.is_available === "boolean") &&
    typeof value.observed_at === "string"
  )
}

function isExchangeRate(value: unknown): value is ExchangeRate {
  return (
    isRecord(value) && Number.isInteger(value.id) && typeof value.source === "string" &&
    typeof value.rate_type === "string" &&
    (value.rate_side === "reference" || value.rate_side === "buy" || value.rate_side === "sell") &&
    typeof value.base_currency === "string" && typeof value.quote_currency === "string" &&
    isDecimal(value.rate) && typeof value.observed_at === "string"
  )
}

function queryString(params: object): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string" || typeof value === "number") {
      searchParams.set(key, String(value))
    }
  }
  const query = searchParams.toString()
  return query ? `?${query}` : ""
}

/** Cliente de API para el catálogo canónico. */
export const apiClient: ApiClient = {
  fetchStores: async (signal) => {
    const result: unknown = await request<unknown>("/api/v1/stores", { signal })
    if (!Array.isArray(result) || !result.every(isStore)) {
      throw new ApiError("PriceScope API devolvió un listado de tiendas inesperado.")
    }
    return result
  },

  fetchProducts: async (params, signal) => {
    const searchParams = new URLSearchParams()
    if (params?.category_id != null) {
      searchParams.set("category_id", String(params.category_id))
    }
    if (params?.search?.trim()) searchParams.set("search", params.search.trim())
    if (params?.limit != null) {
      searchParams.set("limit", String(params.limit))
    }
    if (params?.offset != null) {
      searchParams.set("offset", String(params.offset))
    }
    const path = `/api/v1/products/paginated?${searchParams.toString()}`
    const result: unknown = await request<unknown>(path, { signal })
    if (
      !isRecord(result) ||
      !Array.isArray(result.items) ||
      !result.items.every(isProduct) ||
      !Number.isInteger(result.total) ||
      !Number.isInteger(result.limit) ||
      !Number.isInteger(result.offset)
    ) {
      throw new ApiError("PriceScope API devolvió un formato de productos paginados inesperado.")
    }
    return result as unknown as PaginatedProducts
  },

  fetchProductsWithPrices: async (params, signal) => {
    const searchParams = new URLSearchParams()
    if (params?.category_id != null) searchParams.set("category_id", String(params.category_id))
    if (params?.search?.trim()) searchParams.set("search", params.search.trim())
    if (params?.start) searchParams.set("start", params.start)
    if (params?.end) searchParams.set("end", params.end)
    if (params?.limit != null) searchParams.set("limit", String(params.limit))
    if (params?.offset != null) searchParams.set("offset", String(params.offset))
    const result: unknown = await request<unknown>(
      `/api/v1/products/paginated-with-prices?${searchParams.toString()}`, { signal },
    )
    if (!isRecord(result) || !Array.isArray(result.items) || !result.items.every(isPricedProduct) ||
        !Number.isInteger(result.total) || !Number.isInteger(result.limit) || !Number.isInteger(result.offset)) {
      throw new ApiError("PriceScope API devolvió un listado de productos con precios inesperado.")
    }
    return result as unknown as PricedProductPage
  },

  fetchCategories: async (signal) => {
    const result: unknown = await request<unknown>(`/api/v1/categories`, { signal })
    if (!Array.isArray(result) || !result.every(isCategory)) {
      throw new ApiError("PriceScope API devolvió un formato de categorías inesperado.")
    }
    return result
  },

  fetchPriceObservations: async (params, signal) => {
    const result: unknown = await request<unknown>(
      `/api/v1/price-observations${queryString(params ?? {})}`,
      { signal },
    )
    if (!Array.isArray(result) || !result.every(isPriceObservation)) {
      throw new ApiError("PriceScope API devolvió observaciones de precio inesperadas.")
    }
    return result
  },

  fetchExchangeRates: async (params, signal) => {
    // Render's public contract requires a rate type. Callers can explicitly
    // request another stored type (for example "blue"); no quote is synthesized.
    const query = { ...params, rate_type: params?.rate_type ?? "official" }
    const result: unknown = await request<unknown>(
      `/api/v1/exchange-rates${queryString(query)}`,
      { signal },
    )
    if (!Array.isArray(result) || !result.every(isExchangeRate)) {
      throw new ApiError("PriceScope API devolvió cotizaciones inesperadas.")
    }
    return result
  },

  fetchComparisons: async (params, signal) => {
    const result: unknown = await request<unknown>(`/api/v1/comparisons${queryString(params ?? {})}`, { signal })
    if (!Array.isArray(result) || !result.every((item) => isRecord(item) &&
      Number.isInteger(item.product_id) && typeof item.product_name === "string" &&
      Array.isArray(item.prices) && Number.isInteger(item.prices.length) &&
      typeof item.currency === "string" && typeof item.spread_amount === "string")) {
      throw new ApiError("PriceScope API devolvio comparativas inesperadas.")
    }
    return result as PriceComparison[]
  },

  fetchAlerts: async (params, signal) => {
    const result: unknown = await request<unknown>(`/api/v1/alerts${queryString(params ?? {})}`, { signal })
    if (!Array.isArray(result) || !result.every((item) => isRecord(item) &&
      (item.alert_type === "price_spike" || item.alert_type === "price_increase_over_currency") &&
      Number.isInteger(item.product_id) && typeof item.product_name === "string" &&
      Number.isInteger(item.store_id) && typeof item.price_change_percent === "string")) {
      throw new ApiError("PriceScope API devolvio alertas inesperadas.")
    }
    return result as PriceAlert[]
  },

  fetchInflation: async (params, signal) => {
    const result: unknown = await request<unknown>(`/api/v1/indicators/inflation${queryString(params)}`, { signal })
    if (!isRecord(result) || (result.status !== "available" && result.status !== "insufficient_data") ||
      !Array.isArray(result.currencies) || !Array.isArray(result.categories) || !Array.isArray(result.products)) {
      throw new ApiError("PriceScope API devolvio un indicador de inflacion inesperado.")
    }
    return result as unknown as InflationResult
  },

  fetchShrinkflation: async (params, signal) => {
    const result: unknown = await request<unknown>(`/api/v1/indicators/shrinkflation${queryString(params ?? {})}`, { signal })
    if (!Array.isArray(result) || !result.every((item) => isRecord(item) &&
      (item.status === "confirmed" || item.status === "possible") &&
      Number.isInteger(item.product_id) && typeof item.unit_price_change_percent === "string")) {
      throw new ApiError("PriceScope API devolvio senales de reduflacion inesperadas.")
    }
    return result as ShrinkflationSignal[]
  },

  verifyAdminToken: async (token) => {
    const result: unknown = await request<unknown>("/api/v1/management/access", {
      headers: { "X-Admin-Token": token },
    })
    return isRecord(result) && result.can_manage === true
  },

  fetchManagedStores: async (signal) => {
    const result: unknown = await request<unknown>("/api/v1/management/stores", { signal })
    if (!Array.isArray(result) || !result.every(isManagedStore)) {
      throw new ApiError("PriceScope API devolvió un listado de tiendas inesperado.")
    }
    return result
  },

  createStore: async (input) => requireManagedStore(await request<unknown>("/api/v1/management/stores", {
    method: "POST",
    body: JSON.stringify(input),
  })),

  analyzeStore: async (storeId) => requireManagedStore(await request<unknown>(
    `/api/v1/management/stores/${storeId}/analyze`, { method: "POST" },
  )),

  saveStoreMonitoring: async (storeId, input) => requireManagedStore(await request<unknown>(
    `/api/v1/management/stores/${storeId}/monitoring`, {
      method: "PUT",
      body: JSON.stringify(input),
    },
  )),

  extractStore: async (storeId) => {
    const result: unknown = await request<unknown>(`/api/v1/management/stores/${storeId}/extract`, { method: "POST" })
    if (!isExtractionRun(result)) throw new ApiError("PriceScope API devolvió un resultado de extracción inesperado.")
    return result
  },

  fetchStoreExtractions: async (storeId, limit = 10, signal) => {
    const result: unknown = await request<unknown>(
      `/api/v1/management/stores/${storeId}/extractions?limit=${limit}`, { signal },
    )
    if (!Array.isArray(result) || !result.every(isExtractionRun)) {
      throw new ApiError("PriceScope API devolvió un historial de extracciones inesperado.")
    }
    return result
  },
}
