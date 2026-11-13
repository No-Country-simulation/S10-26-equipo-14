import { useEffect, useMemo, useState } from "react"
import { Activity, BellRing, CheckCircle2 } from "lucide-react"

import { apiClient } from "@/lib/api"
import { deriveMarketAlerts, loadResource, reachedRecordLimit, type MarketAlertKind, type ResourceState } from "@/lib/marketAlerts.js"
import type { Category, ExchangeRate, PriceObservation, Product } from "@/types"
import type { ManagedStore } from "@/types/store"
import type { StoreProduct } from "@/types/storeProduct"

function tone(kind: MarketAlertKind) {
  if (["price_up", "extraction_failed"].includes(kind)) return "border-rose-200 bg-rose-50 text-rose-900"
  if (["price_down", "new_minimum", "extraction_success"].includes(kind)) return "border-emerald-200 bg-emerald-50 text-emerald-900"
  if (["stale_price", "stale_fx", "extraction_partial"].includes(kind)) return "border-amber-200 bg-amber-50 text-amber-950"
  return "border-indigo-200 bg-indigo-50 text-indigo-950"
}

type AlertResource = "stores" | "categories" | "products" | "listings" | "observations" | "officialRates" | "parallelRates" | "eligibleStores"
type AlertResourceStates = Record<AlertResource, ResourceState<unknown>>
const LOADING_RESOURCE: ResourceState<unknown> = { status: "loading", data: null, error: null }

export default function AlertasPage() {
  const [stores, setStores] = useState<ManagedStore[]>([])
  const [eligibleStoreIds, setEligibleStoreIds] = useState<number[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [listings, setListings] = useState<StoreProduct[]>([])
  const [observations, setObservations] = useState<PriceObservation[]>([])
  const [rates, setRates] = useState<ExchangeRate[]>([])
  const [storeId, setStoreId] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [threshold, setThreshold] = useState(5)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [states, setStates] = useState<AlertResourceStates>({
    stores: LOADING_RESOURCE, categories: LOADING_RESOURCE, products: LOADING_RESOURCE,
    listings: LOADING_RESOURCE, observations: LOADING_RESOURCE, officialRates: LOADING_RESOURCE,
    parallelRates: LOADING_RESOURCE, eligibleStores: LOADING_RESOURCE,
  })
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setStates((current) => Object.fromEntries(Object.keys(current).map((key) => [key, LOADING_RESOURCE])) as AlertResourceStates)
    const query = {
      store_id: storeId ? Number(storeId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      start: start ? `${start}T00:00:00Z` : undefined,
      end: end ? `${end}T23:59:59.999Z` : undefined,
      limit: 1000,
    }
    void Promise.all([
      loadResource(apiClient.fetchManagedStores(controller.signal)),
      loadResource(apiClient.fetchCategories(controller.signal)),
      loadResource(apiClient.fetchProducts({ limit: 100, offset: 0 }, controller.signal)),
      loadResource(apiClient.fetchStoreProducts(undefined, controller.signal)),
      loadResource(apiClient.fetchPriceObservations(query, controller.signal)),
      loadResource(apiClient.fetchExchangeRates({ rate_type: "official", start: query.start, end: query.end, limit: 1000 }, controller.signal)),
      loadResource(apiClient.fetchExchangeRates({ rate_type: "parallel", start: query.start, end: query.end, limit: 1000 }, controller.signal)),
      loadResource(apiClient.fetchStores(controller.signal, {
        with_observations: true, eligible_for: "alerts", category_id: query.category_id,
        start: query.start, end: query.end,
      })),
    ]).then(([managed, nextCategories, productPage, nextListings, nextObservations, official, parallel, eligibleStores]) => {
      if (controller.signal.aborted) return
      setStates({ stores: managed, categories: nextCategories, products: productPage, listings: nextListings,
        observations: nextObservations, officialRates: official, parallelRates: parallel, eligibleStores })
      if (managed.status !== "error") setStores(managed.data)
      if (eligibleStores.status !== "error") setEligibleStoreIds(eligibleStores.data.map((store) => store.id))
      if (nextCategories.status !== "error") setCategories(nextCategories.data)
      if (productPage.status !== "error") setProducts(productPage.data.items)
      if (nextListings.status !== "error") setListings(nextListings.data)
      if (nextObservations.status !== "error") setObservations(nextObservations.data)
      setRates((current) => [
        ...(official.status === "error" ? current.filter((rate) => rate.rate_type === "official") : official.data),
        ...(parallel.status === "error" ? current.filter((rate) => rate.rate_type === "parallel") : parallel.data),
      ])
      if (eligibleStores.status !== "error") setStoreId((current) => current && eligibleStores.data.some((store) => store.id === Number(current)) ? current : "")
    }).catch((cause: unknown) => {
      if (cause instanceof Error && cause.name !== "AbortError") setError(cause.message)
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [categoryId, end, retry, start, storeId])

  const alerts = useMemo(() => deriveMarketAlerts({ observations, listings, products, stores, rates, threshold,
    categoryId: categoryId ? Number(categoryId) : null, storeId: storeId ? Number(storeId) : null }),
    [categoryId, listings, observations, products, rates, storeId, stores, threshold])
  const priceStates = [states.observations, states.listings, states.products, states.stores]
  const rateStates = [states.officialRates, states.parallelRates]
  const extractionStates = [states.stores]
  const priceErrors = priceStates.filter((state) => state.status === "error").map((state) => state.error)
  const rateErrors = rateStates.filter((state) => state.status === "error").map((state) => state.error)
  const extractionErrors = extractionStates.filter((state) => state.status === "error").map((state) => state.error)
  const alertLoading = [...priceStates, ...rateStates, ...extractionStates].some((state) => state.status === "loading")
  const hiddenKinds = new Set<MarketAlertKind>([
    ...(priceErrors.length ? ["price_up", "price_down", "new_minimum", "stale_price"] as MarketAlertKind[] : []),
    ...(rateErrors.length ? ["fx_change", "stale_fx"] as MarketAlertKind[] : []),
    ...(extractionErrors.length ? ["extraction_failed", "extraction_partial", "extraction_success"] as MarketAlertKind[] : []),
  ])
  const visibleAlerts = alerts.filter((item) => !hiddenKinds.has(item.kind))
  const filterErrors = [states.categories, states.eligibleStores]
    .filter((state) => state.status === "error").map((state) => state.error)
  const realProductIds = new Set(products.filter((product) => !product.name.startsWith("DEMO PriceScope ")).map((product) => product.id))
  const comparableObservationCount = observations.filter((row) => row.is_available !== false &&
    listings.some((listing) => row.store_product_id === listing.id && listing.product_id !== null &&
      realProductIds.has(listing.product_id) && !listing.product_name.startsWith("DEMO PriceScope "))).length

  return (
    <section className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-slate-900">Alertas de precios y cobertura</h1><p className="mt-1 max-w-3xl text-sm text-slate-600">Eventos derivados de observaciones reales consecutivas, cotizaciones guardadas y el último estado de extracción. Son señales de muestra, no pronósticos.</p></div>
        <button type="button" onClick={() => setRetry((value) => value + 1)} className="h-9 rounded-lg border border-slate-300 px-3 text-sm font-semibold">Actualizar</button>
      </header>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
        <label className="text-xs font-medium text-slate-600">Tienda<select value={storeId} onChange={(event) => setStoreId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"><option value="">Todas las elegibles</option>{stores.filter((store) => store.is_active && eligibleStoreIds.includes(store.id)).map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">Categoría<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"><option value="">Todas</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">Umbral de variación (%)<input type="number" min="0.1" max="100" step="0.5" value={threshold} onChange={(event) => setThreshold(Math.max(0.1, Number(event.target.value) || 5))} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
        <label className="text-xs font-medium text-slate-600">Desde<input type="date" value={start} onChange={(event) => setStart(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
        <label className="text-xs font-medium text-slate-600">Hasta<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
        <div className="self-end pb-2 text-xs text-slate-500">{comparableObservationCount} observaciones disponibles</div>
      </div>

      {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {filterErrors.length > 0 && <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Error de API en filtros: {filterErrors.join("; ")}</p>}
      {reachedRecordLimit(observations, 1000) ||
        (Array.isArray(states.officialRates.data) && reachedRecordLimit(states.officialRates.data, 1000)) ||
        (Array.isArray(states.parallelRates.data) && reachedRecordLimit(states.parallelRates.data, 1000))
        ? <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Una o más consultas alcanzaron el límite de 1.000 registros; el cálculo puede estar truncado. Reduce el período o aplica filtros.</p>
        : null}
      {alertLoading || loading ? <p role="status" className="py-12 text-center text-sm text-slate-500">Cargando los módulos de alertas…</p> : <>
      {(priceErrors.length > 0 || rateErrors.length > 0 || extractionErrors.length > 0) && <div role="alert" className="mb-3 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"><Activity className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /><div><p className="font-semibold">Algunos tipos de alerta no están disponibles por errores de API.</p><ul className="mt-2 list-inside list-disc">{[...priceErrors, ...rateErrors, ...extractionErrors].map((item, index) => <li key={index}>{item}</li>)}</ul>{visibleAlerts.length > 0 && <p className="mt-2">Se muestran únicamente los módulos que cargaron correctamente.</p>}</div></div>}
      {visibleAlerts.length === 0 ? <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="h-1 bg-gradient-to-r from-[#0b2e50] via-cyan-500 to-sky-400" /><div className="px-6 py-12 text-center sm:px-12"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-50 text-cyan-700"><BellRing className="h-7 w-7" aria-hidden="true" /></div><h2 className="mt-5 text-xl font-semibold tracking-tight text-[#0b2e50]">{priceErrors.length && rateErrors.length && extractionErrors.length ? "Alertas no disponibles" : "No hay alertas disponibles por el momento"}</h2><p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-600">{priceErrors.length || rateErrors.length || extractionErrors.length ? "Los errores anteriores impiden calcular algunas categorías. Intenta actualizar cuando la API vuelva a estar disponible." : `Las alertas aparecerán cuando haya historial comparable suficiente para identificar variaciones verificables que superen el umbral del ${threshold}%.`}</p>{!(priceErrors.length && rateErrors.length && extractionErrors.length) && <div role="status" className="mx-auto mt-6 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-4 w-4" aria-hidden="true" />Módulo operativo · datos verificados</div>}</div></div> : <div className="space-y-3">{visibleAlerts.map((alert) => <article key={alert.key} className={`rounded-xl border p-4 ${tone(alert.kind)}`}>
        <div className="flex flex-wrap items-start justify-between gap-2"><div><h2 className="font-semibold">{alert.title}{alert.productName ? ` · ${alert.productName}` : ""}</h2><p className="mt-1 text-sm">{alert.storeName ? `${alert.storeName} · ` : ""}{alert.detail}</p></div><time className="text-xs">{alert.observedAt ? new Date(alert.observedAt).toLocaleString("es-AR") : "Fecha no disponible"}</time></div>
        {(alert.previousValue || alert.currentValue) && <p className="mt-2 text-sm">{alert.previousValue && <><span>{alert.previousValue}</span>{alert.previousAt && <span className="ml-1 text-xs">({new Date(alert.previousAt).toLocaleDateString("es-AR")})</span>} <span aria-hidden="true">→</span> </>}{alert.currentValue}{alert.changePercent !== undefined && <strong className="ml-2">{alert.changePercent > 0 ? "+" : ""}{alert.changePercent.toLocaleString("es-AR", { maximumFractionDigits: 2 })}%</strong>}</p>}
        {alert.source && <p className="mt-1 text-xs">Fuente: {alert.source}</p>}
        {alert.sourceUrl && <a className="mt-2 inline-block text-xs font-semibold underline" href={alert.sourceUrl} target="_blank" rel="noreferrer">Ver publicación</a>}
      </article>)}</div>}
      </>}
      <p className="text-xs text-slate-500">Umbral inicial configurable: 5%. Alertas de antigüedad usan 48 horas. Las señales no reemplazan la revisión de la fuente.</p>
    </section>
  )
}
