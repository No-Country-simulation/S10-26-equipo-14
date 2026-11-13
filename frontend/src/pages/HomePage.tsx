import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import MetricCard from "@/components/metrics/MetricCard"
import { ApiError, apiClient, type PriceAlert, type PriceComparison } from "@/lib/api"
import { loadResource, reachedRecordLimit, type ResourceState } from "@/lib/marketAlerts.js"
import type { Category, ExchangeRate, PriceObservation, PricedProduct } from "@/types"
import type { ManagedStore } from "@/types/store"
import type { StoreProduct } from "@/types/storeProduct"

const PERIOD_DAYS = 90
const PAGE_LIMIT = 1000

interface DashboardData {
  stores: ManagedStore[]
  categories: Category[]
  products: PricedProduct[]
  listings: StoreProduct[]
  observations: PriceObservation[]
  rates: ExchangeRate[]
  comparisons: PriceComparison[]
  alerts: PriceAlert[]
}

const EMPTY: DashboardData = {
  stores: [], categories: [], products: [], listings: [], observations: [], rates: [], comparisons: [], alerts: [],
}

type ResourceKey = "stores" | "categories" | "products" | "listings" | "observations" | "officialRates" | "parallelRates" | "comparisons" | "alerts"
type ResourceStates = Record<ResourceKey, ResourceState<unknown>>
const LOADING_STATE: ResourceState<unknown> = { status: "loading", data: null, error: null }
const LOADING_STATES: ResourceStates = {
  stores: LOADING_STATE, categories: LOADING_STATE, products: LOADING_STATE, listings: LOADING_STATE,
  observations: LOADING_STATE, officialRates: LOADING_STATE, parallelRates: LOADING_STATE,
  comparisons: LOADING_STATE, alerts: LOADING_STATE,
}

function message(error: unknown) {
  if (error instanceof ApiError || error instanceof Error) return error.message
  return "No se pudo cargar información del dashboard."
}

function datePeriod() {
  const end = new Date()
  const start = new Date(end)
  start.setUTCDate(start.getUTCDate() - PERIOD_DAYS)
  return {
    start: `${start.toISOString().slice(0, 10)}T00:00:00Z`,
    end: `${end.toISOString().slice(0, 10)}T23:59:59.999Z`,
  }
}

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString("es-AR") : "Sin observaciones"
}

function rateSeries(rates: ExchangeRate[], type: "official" | "parallel") {
  const chosen = rates.filter((rate) => rate.rate_type === type &&
    rate.base_currency === "USD" && rate.quote_currency === "ARS" &&
    (type === "official" ? rate.rate_side === "reference" : rate.rate_side === "sell") &&
    !/demo|synthetic|sint[eé]tic/i.test(rate.source))
  const byDate = new Map<string, ExchangeRate>()
  for (const rate of chosen) {
    const day = rate.observed_at.slice(0, 10)
    const previous = byDate.get(day)
    if (!previous || Date.parse(rate.observed_at) > Date.parse(previous.observed_at)) byDate.set(day, rate)
  }
  return [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([date, rate]) => ({
    date,
    [type]: Number(rate.rate),
  }))
}

function priceHistory(data: DashboardData, productId: number, currency: string) {
  const productListings = new Map(data.listings
    .filter((listing) => listing.product_id === productId && !listing.product_name.startsWith("DEMO PriceScope "))
    .map((listing) => [listing.id, listing]))
  const rows = data.observations.filter((observation) => observation.currency === currency &&
    observation.is_available !== false && productListings.has(observation.store_product_id))
  const latestByStoreDay = new Map<string, PriceObservation>()
  for (const observation of rows) {
    const listing = productListings.get(observation.store_product_id)
    if (!listing) continue
    const key = `${listing.store_id}:${observation.observed_at.slice(0, 10)}`
    const prior = latestByStoreDay.get(key)
    if (!prior || Date.parse(observation.observed_at) > Date.parse(prior.observed_at)) latestByStoreDay.set(key, observation)
  }
  const stores = [...new Set([...latestByStoreDay.keys()].map((key) => Number(key.split(":")[0])))]
    .map((id) => data.stores.find((store) => store.id === id))
    .filter((store): store is ManagedStore => Boolean(store))
  const dates = [...new Set([...latestByStoreDay.values()].map((row) => row.observed_at.slice(0, 10)))].sort()
  const series = stores.map((store) => ({
    store,
    count: dates.filter((date) => latestByStoreDay.has(`${store.id}:${date}`)).length,
  })).filter((item) => item.count >= 2)
  const chartData = dates.map((date) => {
    const point: Record<string, string | number | null> = { date }
    for (const store of stores) {
      const observation = latestByStoreDay.get(`${store.id}:${date}`)
      point[`store-${store.id}`] = observation ? Number(
        observation.promotional_price && Number(observation.promotional_price) <= Number(observation.amount)
          ? observation.promotional_price : observation.amount,
      ) : null
    }
    return point
  })
  return { rows, stores, series, dates, chartData }
}

export default function HomePage() {
  const [data, setData] = useState<DashboardData>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [states, setStates] = useState<ResourceStates>(LOADING_STATES)
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null)
  const [selectedCurrency, setSelectedCurrency] = useState("ARS")
  const [retry, setRetry] = useState(0)
  const period = useMemo(() => datePeriod(), [])

  useEffect(() => {
    const controller = new AbortController()
    let active = true
    setLoading(true)
    setError(null)
    setStates({ ...LOADING_STATES })
    void Promise.all([
      loadResource(apiClient.fetchManagedStores(controller.signal)),
      loadResource(apiClient.fetchCategories(controller.signal)),
      loadResource(apiClient.fetchProductsWithPrices({ limit: 100, offset: 0 }, controller.signal)),
      loadResource(apiClient.fetchStoreProducts(undefined, controller.signal)),
      loadResource(apiClient.fetchPriceObservations({ start: period.start, end: period.end, limit: PAGE_LIMIT }, controller.signal)),
      loadResource(apiClient.fetchExchangeRates({ rate_type: "official", start: period.start, end: period.end, limit: PAGE_LIMIT }, controller.signal)),
      loadResource(apiClient.fetchExchangeRates({ rate_type: "parallel", start: period.start, end: period.end, limit: PAGE_LIMIT }, controller.signal)),
      loadResource(apiClient.fetchComparisons({ start: period.start, end: period.end, limit: 100 }, controller.signal)),
      loadResource(apiClient.fetchAlerts({ start: period.start, end: period.end, spike_percent: 5, limit: 100 }, controller.signal)),
    ]).then(([stores, categories, productPage, listings, observations, official, parallel, comparisons, alerts]) => {
      if (!active) return
      const results = { stores, categories, products: productPage, listings, observations,
        officialRates: official, parallelRates: parallel, comparisons, alerts }
      setStates(results as ResourceStates)
      setData((current) => {
        const nextStores = stores.status === "error" ? current.stores : stores.data
        const nextCategories = categories.status === "error" ? current.categories : categories.data
        const nextProducts = productPage.status === "error" ? current.products : productPage.data.items
        const nextListings = listings.status === "error" ? current.listings : listings.data
        const nextObservations = observations.status === "error" ? current.observations : observations.data
        const nextOfficialRates = official.status === "error" ? current.rates.filter((row) => row.rate_type === "official") : official.data
        const nextParallelRates = parallel.status === "error" ? current.rates.filter((row) => row.rate_type === "parallel") : parallel.data
        const nextComparisons = comparisons.status === "error" ? current.comparisons : comparisons.data
        const nextAlerts = alerts.status === "error" ? current.alerts : alerts.data
        const firstProductId = nextProducts.find((product) => product.latest_price)?.id ?? null
        if (productPage.status !== "error") setSelectedProductId((selected) => selected ?? firstProductId)
        return { stores: nextStores, categories: nextCategories, products: nextProducts, listings: nextListings,
          observations: nextObservations.filter((row) => row.is_available !== false),
          rates: [...nextOfficialRates, ...nextParallelRates], comparisons: nextComparisons, alerts: nextAlerts }
      })
    }).catch((cause: unknown) => {
      if (active && cause instanceof Error && cause.name !== "AbortError") setError(message(cause))
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false; controller.abort() }
  }, [period.end, period.start, retry])

  const moduleState = (keys: ResourceKey[]) => {
    const selected = keys.map((key) => states[key])
    if (selected.some((state) => state.status === "loading")) return { status: "loading" as const }
    const failures = selected.filter((state) => state.status === "error")
    if (failures.length) return { status: "error" as const, error: failures.map((state) => state.error).join("; ") }
    return { status: selected.some((state) => state.status === "available") ? "available" as const : "empty" as const }
  }
  const priceModule = moduleState(["products", "listings", "observations"])
  const rateModule = moduleState(["officialRates", "parallelRates"])
  const comparisonModule = moduleState(["comparisons"])
  const categoryModule = moduleState(["categories", "products"])
  const coverageModule = moduleState(["stores", "listings", "observations"])
  const alertModule = moduleState(["alerts", "stores"])

  const realProducts = data.products.filter((product) => !product.name.startsWith("DEMO PriceScope "))
  const realProductIds = new Set(realProducts.map((product) => product.id))
  const realListings = data.listings.filter((listing) => listing.product_id !== null && realProductIds.has(listing.product_id) &&
    !listing.product_name.startsWith("DEMO PriceScope "))
  const listingById = new Map(realListings.map((listing) => [listing.id, listing]))
  const observations = data.observations.filter((observation) => listingById.has(observation.store_product_id))
  const realProductsWithPrices = realProducts.filter((product) => product.latest_price && product.latest_price.is_available !== false)
  const realStoresWithPrices = new Set(observations.map((observation) => listingById.get(observation.store_product_id)?.store_id).filter((id): id is number => id !== undefined))
  const lastObservation = observations.reduce<PriceObservation | null>((latest, row) =>
    !latest || Date.parse(row.observed_at) > Date.parse(latest.observed_at) ? row : latest, null)
  const observationCounts = new Map<number, number>()
  for (const observation of observations) {
    const storeId = listingById.get(observation.store_product_id)?.store_id
    if (storeId !== undefined) observationCounts.set(storeId, (observationCounts.get(storeId) ?? 0) + 1)
  }
  const productId = selectedProductId && realProductIds.has(selectedProductId)
    ? selectedProductId : realProductsWithPrices[0]?.id ?? null
  const selectedProduct = realProducts.find((product) => product.id === productId)
  const productCurrencyOptions = [...new Set(observations.filter((row) =>
    realListings.some((listing) => listing.product_id === productId && listing.id === row.store_product_id),
  ).map((row) => row.currency))]
  const currency = productCurrencyOptions.includes(selectedCurrency) ? selectedCurrency : productCurrencyOptions[0] ?? "ARS"
  const history = productId ? priceHistory({ ...data, observations }, productId, currency) : null
  const historyPrices = history?.rows.map((row) => Number(row.promotional_price !== null && Number(row.promotional_price) <= Number(row.amount) ? row.promotional_price : row.amount)) ?? []
  const historyRange = historyPrices.length
    ? `${Math.min(...historyPrices).toLocaleString("es-AR")}–${Math.max(...historyPrices).toLocaleString("es-AR")} ${currency}`
    : "sin historial"
  const officialRates = rateSeries(data.rates, "official")
  const parallelRates = rateSeries(data.rates, "parallel")
  const fxDates = [...new Set([...officialRates.map((row) => row.date), ...parallelRates.map((row) => row.date)])].sort()
  const fxData = fxDates.map((date) => ({
    date,
    official: officialRates.find((row) => row.date === date)?.official ?? null,
    parallel: parallelRates.find((row) => row.date === date)?.parallel ?? null,
  }))
  const latestFx = data.rates.filter((rate) => !/demo|synthetic|sint[eé]tic/i.test(rate.source))
    .reduce<ExchangeRate | null>((latest, rate) => !latest || Date.parse(rate.observed_at) > Date.parse(latest.observed_at) ? rate : latest, null)
  const categoryCounts = data.categories.map((category) => ({
    category,
    count: realProductsWithPrices.filter((product) => product.category_id === category.id).length,
  })).filter((item) => item.count > 0)
  const recentAlerts = data.stores.filter((store) => store.last_extraction_status &&
    ["BLOCKED", "NETWORK_ERROR", "RATE_LIMITED", "PRODUCT_NOT_FOUND", "PRICE_NOT_FOUND", "PARTIAL_SUCCESS"].includes(store.last_extraction_status))

  return (
    <section className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">Muestra observada · últimos {PERIOD_DAYS} días</p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Inteligencia de precios</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">Indicadores descriptivos de registros observados por PriceScope. No representan IPC oficial ni inflación general del mercado.</p>
        </div>
        <button type="button" onClick={() => setRetry((value) => value + 1)} className="h-10 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50">Actualizar datos</button>
      </header>

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><p>{error}</p><button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-2 font-semibold underline">Reintentar</button></div>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Productos con precio real" value={states.products.status === "loading" ? "…" : states.products.status === "error" ? "Error API" : realProductsWithPrices.length} subtitle={states.products.status === "error" ? states.products.error : `de ${realProducts.length} productos reales registrados`} />
        <MetricCard title="Tiendas con observaciones" value={states.observations.status === "loading" || states.stores.status === "loading" ? "…" : states.observations.status === "error" || states.stores.status === "error" ? "Error API" : realStoresWithPrices.size} subtitle={states.observations.status === "error" ? states.observations.error : states.stores.status === "error" ? states.stores.error : "con precios disponibles en el período"} />
        <MetricCard title="Observaciones válidas" value={states.observations.status === "loading" ? "…" : states.observations.status === "error" ? "Error API" : observations.length} subtitle={states.observations.status === "error" ? states.observations.error : "no demo · disponibles o disponibilidad desconocida"} />
        <MetricCard title="Última actualización de precios" value={states.observations.status === "loading" ? "…" : states.observations.status === "error" ? "Error API" : lastObservation ? new Date(lastObservation.observed_at).toLocaleDateString("es-AR") : "Sin datos"} subtitle={states.observations.status === "error" ? states.observations.error : lastObservation ? formatDate(lastObservation.observed_at) : "No hay observaciones en el período"} />
        <MetricCard title="Alertas de precios" value={states.alerts.status === "loading" ? "…" : states.alerts.status === "error" ? "Error API" : data.alerts.length} subtitle={states.alerts.status === "error" ? states.alerts.error : "aumentos desde 5% o sobre la variación cambiaria"} />
      </div>

      {(reachedRecordLimit(data.observations, PAGE_LIMIT) || reachedRecordLimit(data.rates.filter((rate) => rate.rate_type === "official"), PAGE_LIMIT) || reachedRecordLimit(data.rates.filter((rate) => rate.rate_type === "parallel"), PAGE_LIMIT)) && (
        <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Una o más consultas alcanzaron el límite de {PAGE_LIMIT.toLocaleString("es-AR")} registros. Los gráficos pueden estar truncados; reduce el período o filtra la consulta.</p>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h2 className="font-semibold text-slate-900">Evolución de precios</h2><p className="mt-1 text-xs text-slate-500">Última observación diaria por tienda · moneda original · {period.start.slice(0, 10)} a {period.end.slice(0, 10)}</p></div>
            <div className="flex gap-2">
              <select aria-label="Producto del gráfico" value={productId ?? ""} onChange={(event) => setSelectedProductId(event.target.value ? Number(event.target.value) : null)} className="h-9 max-w-48 rounded-lg border border-slate-300 bg-white px-2 text-sm">
                <option value="">Producto</option>{realProductsWithPrices.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
              </select>
              <select aria-label="Moneda del gráfico" value={currency} onChange={(event) => setSelectedCurrency(event.target.value)} className="h-9 rounded-lg border border-slate-300 bg-white px-2 text-sm">{productCurrencyOptions.map((value) => <option key={value}>{value}</option>)}</select>
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">{selectedProduct?.name ?? "Elige un producto"} · {history?.rows.length ?? 0} observaciones · origen: API de PriceScope</p>
          {priceModule.status === "loading" ? <div className="flex h-64 items-center justify-center text-sm text-slate-500">Cargando series reales…</div> : priceModule.status === "error" ? <div role="alert" className="flex h-64 items-center justify-center rounded-lg bg-rose-50 p-6 text-center text-sm text-rose-800">Error de API: {priceModule.error}</div> : priceModule.status === "empty" || !history || history.series.length === 0 ? <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">{priceModule.status === "empty" ? "Sin observaciones en este período." : "Historial insuficiente: se requieren observaciones en al menos dos fechas para una tienda."} No se interpolan fechas faltantes.</div> : <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={history.chartData} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} tickFormatter={(value: number) => value.toLocaleString("es-AR")} /><Tooltip formatter={(value) => [`${currency} ${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`, "Precio"]} /><Legend />
              {history.series.map(({ store }) => <Line key={store.id} dataKey={`store-${store.id}`} name={store.name} type="linear" strokeWidth={2} stroke={`hsl(${(store.id * 67) % 360} 62% 45%)`} dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false} />)}
            </LineChart></ResponsiveContainer>
          </div>}
          {history && <>
            <p className="mt-2 text-xs text-slate-500">Rango observado: {historyRange} · {history.rows.filter((row) => row.promotional_price !== null && Number(row.promotional_price) <= Number(row.amount)).length} observaciones promocionales verificables.</p>
            <ul className="mt-2 divide-y divide-slate-100">{[...history.rows].sort((a, b) => Date.parse(b.observed_at) - Date.parse(a.observed_at)).slice(0, 4).map((row) => {
              const listing = listingById.get(row.store_product_id)
              const promo = row.promotional_price !== null && Number(row.promotional_price) <= Number(row.amount)
              return <li key={row.id} className="flex flex-wrap justify-between gap-2 py-2 text-xs"><span>{data.stores.find((store) => store.id === listing?.store_id)?.name ?? "Tienda"} · {formatDate(row.observed_at)} · {row.currency} {row.amount}{promo ? ` · promo ${row.promotional_price}` : ""}</span>{row.source_url ? <a className="font-semibold text-indigo-700 underline" href={row.source_url} target="_blank" rel="noreferrer">Fuente</a> : <span className="text-slate-400">Fuente sin URL</span>}</li>
            })}</ul>
          </>}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div><h2 className="font-semibold text-slate-900">Cotización USD/ARS</h2><p className="mt-1 text-xs text-slate-500">Oficial referencia frente a paralelo venta · ARS por USD · {data.rates.filter((rate) => !/demo|synthetic|sint[eé]tic/i.test(rate.source)).length} cotizaciones</p></div>
          {rateModule.status === "loading" ? <div className="flex h-64 items-center justify-center text-sm text-slate-500">Cargando cotizaciones…</div> : rateModule.status === "error" ? <div role="alert" className="flex h-64 items-center justify-center rounded-lg bg-rose-50 p-6 text-center text-sm text-rose-800">Error de API: {rateModule.error}</div> : rateModule.status === "empty" || (!officialRates.length && !parallelRates.length) ? <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">Sin cotizaciones reales para este período.</div> : officialRates.length < 2 && parallelRates.length < 2 ? <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">Historial insuficiente: una sola fecha no demuestra evolución cambiaria.</div> : <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%"><LineChart data={fxData} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} tickFormatter={(value: number) => value.toLocaleString("es-AR")} /><Tooltip formatter={(value, name) => [`ARS ${Number(value).toLocaleString("es-AR", { maximumFractionDigits: 2 })}`, name]} /><Legend />
              <Line dataKey="official" name="Oficial · referencia" stroke="#4f46e5" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} /><Line dataKey="parallel" name="Paralelo · venta" stroke="#e11d48" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            </LineChart></ResponsiveContainer>
          </div>}
          <p className="mt-2 text-xs text-slate-500">Última cotización: {loading ? "…" : latestFx ? `${latestFx.source} · ${formatDate(latestFx.observed_at)}` : "Sin datos"}. Las fuentes DEMO se excluyen.</p>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2">
          <h2 className="font-semibold text-slate-900">Comparativa entre comercios</h2><p className="mt-1 text-xs text-slate-500">Mismo producto canónico y moneda · última observación disponible por publicación · {data.comparisons.length} productos comparables.</p>
          {comparisonModule.status === "loading" ? <p className="py-10 text-center text-sm text-slate-500">Cargando comparativas…</p> : comparisonModule.status === "error" ? <p role="alert" className="py-10 text-center text-sm text-rose-800">Error de API: {comparisonModule.error}</p> : comparisonModule.status === "empty" || !data.comparisons.length ? <p className="py-10 text-center text-sm text-slate-500">Sin comparativas para este período; se requieren productos compartidos y moneda compatible.</p> : <div className="mt-4 space-y-3">{data.comparisons.slice(0, 8).map((item) => <article key={item.product_id} className="rounded-lg border border-slate-100 p-3">
            <div className="flex flex-wrap justify-between gap-2"><strong className="text-sm text-slate-800">{item.product_name}</strong><span className="text-xs text-slate-500">{item.currency} · {item.prices.length} precios · diferencia {item.spread_percent === null ? "—" : `${Number(item.spread_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`}</span></div>
            <ul className="mt-2 grid gap-2 sm:grid-cols-2">{item.prices.map((price) => <li key={price.store_product_id} className="flex justify-between gap-2 text-xs"><span>{price.store_name} · {formatDate(price.observed_at)}</span><strong>{item.currency} {Number(price.effective_price).toLocaleString("es-AR", { maximumFractionDigits: 2 })}</strong></li>)}</ul>
          </article>)}</div>}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold text-slate-900">Productos por categoría</h2><p className="mt-1 text-xs text-slate-500">Productos reales con precio observado.</p>
          {categoryModule.status === "loading" ? <p className="py-8 text-sm text-slate-500">Cargando…</p> : categoryModule.status === "error" ? <p role="alert" className="mt-6 text-sm text-rose-800">Error de API: {categoryModule.error}</p> : categoryModule.status === "empty" || !categoryCounts.length ? <p className="mt-6 text-sm text-slate-500">Sin productos con precio en estas categorías.</p> : <ul className="mt-4 space-y-3">{categoryCounts.map(({ category, count }) => <li key={category.id} className="flex justify-between gap-2 text-sm"><span>{category.name}</span><strong>{count}</strong></li>)}</ul>}
          <div className="mt-6 border-t border-slate-100 pt-4"><h3 className="text-sm font-semibold text-slate-800">Señales y extracciones</h3>{alertModule.status === "loading" ? <p className="mt-2 text-xs text-slate-500">Cargando alertas…</p> : alertModule.status === "error" ? <p role="alert" className="mt-2 text-xs text-rose-800">Error de API: {alertModule.error}</p> : <>
            {data.alerts.length ? <ul className="mt-2 space-y-2">{data.alerts.slice(0, 3).map((alert) => <li key={`${alert.store_product_id}-${alert.alert_type}-${alert.observed_at}`} className="text-xs text-rose-800">{alert.product_name} · {alert.store_name} · +{Number(alert.price_change_percent).toLocaleString("es-AR", { maximumFractionDigits: 1 })}%</li>)}</ul> : <p className="mt-2 text-xs text-slate-500">Sin alertas de variación con datos suficientes en el período.</p>}
            {recentAlerts.length > 0 && <p className="mt-2 text-xs text-amber-800">Últimas extracciones con error/parciales: {recentAlerts.slice(0, 2).map((store) => `${store.name} (${store.last_extraction_status})`).join(" · ")}</p>}
            <Link to="/alertas" className="mt-3 inline-block text-xs font-semibold text-indigo-700 underline">Ver alertas y cobertura</Link>
          </>}</div>
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="font-semibold text-slate-900">Cobertura por tienda</h2><p className="mt-1 text-xs text-slate-500">La cobertura operativa requiere conector verificado y observaciones persistidas en una ejecución exitosa.</p></div><span className="text-xs text-slate-500">Último dato: {loading ? "…" : formatDate(lastObservation?.observed_at)}</span></div>
        {coverageModule.status === "loading" ? <p className="py-8 text-sm text-slate-500">Cargando cobertura…</p> : coverageModule.status === "error" ? <p role="alert" className="py-8 text-sm text-rose-800">Error de API: {coverageModule.error}</p> : coverageModule.status === "empty" || data.stores.length === 0 ? <p className="py-8 text-sm text-slate-500">Sin datos de cobertura.</p> : <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="text-xs uppercase text-slate-500"><tr><th className="py-2">Tienda</th><th>Estado del conector</th><th>Última ejecución</th><th>Observaciones</th><th>Último precio</th></tr></thead><tbody className="divide-y divide-slate-100">{data.stores.filter((store) => !store.name.startsWith("DEMO PriceScope ")).map((store) => {
          const latest = observations.filter((row) => listingById.get(row.store_product_id)?.store_id === store.id).reduce<PriceObservation | null>((found, row) => !found || Date.parse(row.observed_at) > Date.parse(found.observed_at) ? row : found, null)
          return <tr key={store.id}><td className="py-2 font-medium">{store.name}</td><td>{store.coverage_status.replaceAll("_", " ")}</td><td>{store.last_extraction_status ?? "Sin ejecuciones"}</td><td>{observationCounts.get(store.id) ?? 0}</td><td>{formatDate(latest?.observed_at)}</td></tr>
        })}</tbody></table></div>}
      </section>
    </section>
  )
}
