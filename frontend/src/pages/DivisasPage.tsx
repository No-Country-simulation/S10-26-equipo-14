import React from "react"

import DualAxisTimeSeriesChart from "@/components/charts/DualAxisTimeSeriesChart"
import FilterBar, { type FilterState } from "@/components/filters/FilterBar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ApiError, apiClient } from "@/lib/api"
import { isDemoName, isSyntheticSource } from "@/lib/marketRecords.js"
import type { Category, ExchangeRate, PriceObservation, Store } from "@/types"
import type { StoreProduct } from "@/types/storeProduct"

const PAGE_LIMIT = 1000
const REQUEST_TIMEOUT_MS = 20_000

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return "No se pudieron cargar las observaciones de PriceScope."
}

function groupByTimestamp(items: { observed_at: string; value: number }[]) {
  const grouped = new Map<string, { total: number; count: number }>()
  for (const item of items) {
    const timestamp = new Date(item.observed_at)
    if (Number.isNaN(timestamp.getTime()) || !Number.isFinite(item.value)) continue
    const key = timestamp.toISOString()
    const current = grouped.get(key) ?? { total: 0, count: 0 }
    grouped.set(key, { total: current.total + item.value, count: current.count + 1 })
  }
  return Array.from(grouped.entries()).sort(([left], [right]) => left.localeCompare(right)).map(([date, data]) => ({
    date,
    value: data.total / data.count,
  }))
}

function mergeSeries(
  priceByDate: { date: string; value: number }[],
  rateByDate: { date: string; value: number }[],
  parallelByDate: { date: string; value: number }[],
) {
  const allDates = new Set([...priceByDate.map((item) => item.date), ...rateByDate.map((item) => item.date), ...parallelByDate.map((item) => item.date)])
  const priceMap = new Map(priceByDate.map((item) => [item.date, item.value]))
  const rateMap = new Map(rateByDate.map((item) => [item.date, item.value]))
  const parallelMap = new Map(parallelByDate.map((item) => [item.date, item.value]))
  return Array.from(allDates).sort().map((date) => ({
    date,
    price: priceMap.get(date) ?? null,
    rate: rateMap.get(date) ?? null,
    parallelRate: parallelMap.get(date) ?? null,
  }))
}

function dateBoundary(date: string | null, endOfDay = false): string | undefined {
  if (!date) return undefined
  return `${date}T${endOfDay ? "23:59:59.999" : "00:00:00"}Z`
}

export default function DivisasPage() {
  const [filters, setFilters] = React.useState<FilterState>({
    storeId: null,
    categoryId: null,
    dateFrom: null,
    dateTo: null,
    search: "",
  })
  const [stores, setStores] = React.useState<Store[]>([])
  const [storeProducts, setStoreProducts] = React.useState<StoreProduct[]>([])
  const [categories, setCategories] = React.useState<Category[]>([])
  const [observations, setObservations] = React.useState<PriceObservation[]>([])
  const [exchangeRates, setExchangeRates] = React.useState<ExchangeRate[]>([])
  const [loadingFilters, setLoadingFilters] = React.useState(true)
  const [loadingSeries, setLoadingSeries] = React.useState(true)
  const [filterErrors, setFilterErrors] = React.useState<string[]>([])
  const [seriesErrors, setSeriesErrors] = React.useState<string[]>([])
  const [retry, setRetry] = React.useState(0)

  const retryRequests = () => {
    setFilterErrors([])
    setSeriesErrors([])
    setLoadingFilters(true)
    setLoadingSeries(true)
    setRetry((value) => value + 1)
  }

  const updateFilters = (next: FilterState) => {
    setLoadingSeries(true)
    setFilters(next)
  }

  React.useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    void Promise.allSettled([
      apiClient.fetchStores(controller.signal),
      apiClient.fetchCategories(controller.signal),
      apiClient.fetchStoreProducts(undefined, controller.signal),
    ])
      .then(([storesResult, categoriesResult, listingsResult]) => {
        if (!active) return
        const errors: string[] = []
        if (storesResult.status === "fulfilled") setStores(storesResult.value)
        else { setStores([]); errors.push("Tiendas: " + errorMessage(storesResult.reason)) }
        if (categoriesResult.status === "fulfilled") setCategories(categoriesResult.value)
        else { setCategories([]); errors.push("Categorías: " + errorMessage(categoriesResult.reason)) }
        if (listingsResult.status === "fulfilled") setStoreProducts(listingsResult.value)
        else { setStoreProducts([]); errors.push("Publicaciones: " + errorMessage(listingsResult.reason)) }
        setFilterErrors(errors)
      })
      .finally(() => {
        window.clearTimeout(timeoutId)
        if (active) setLoadingFilters(false)
      })
    return () => {
      active = false
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [retry])

  React.useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    const query = {
      store_id: filters.storeId ?? undefined,
      category_id: filters.categoryId ?? undefined,
      start: dateBoundary(filters.dateFrom),
      end: dateBoundary(filters.dateTo, true),
      search: filters.search.trim() || undefined,
      limit: PAGE_LIMIT,
    }
    void Promise.allSettled([
      apiClient.fetchPriceObservations(query, controller.signal),
      apiClient.fetchExchangeRates({ rate_type: "official", start: query.start, end: query.end, limit: PAGE_LIMIT }, controller.signal),
      apiClient.fetchExchangeRates({ rate_type: "parallel", start: query.start, end: query.end, limit: PAGE_LIMIT }, controller.signal),
    ])
      .then(([observationsResult, officialResult, parallelResult]) => {
        if (!active) return
        const errors: string[] = []
        if (observationsResult.status === "fulfilled") setObservations(observationsResult.value)
        else { setObservations([]); errors.push("Precios: " + errorMessage(observationsResult.reason)) }
        if (officialResult.status === "fulfilled") setExchangeRates((current) => [...current.filter((row) => row.rate_type !== "official"), ...officialResult.value])
        else { setExchangeRates((current) => current.filter((row) => row.rate_type !== "official")); errors.push("Cotización oficial: " + errorMessage(officialResult.reason)) }
        if (parallelResult.status === "fulfilled") setExchangeRates((current) => [...current.filter((row) => row.rate_type !== "parallel"), ...parallelResult.value])
        else { setExchangeRates((current) => current.filter((row) => row.rate_type !== "parallel")); errors.push("Cotización paralela: " + errorMessage(parallelResult.reason)) }
        setSeriesErrors(errors)
      })
      .finally(() => {
        window.clearTimeout(timeoutId)
        if (active) setLoadingSeries(false)
      })
    return () => {
      active = false
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [filters.categoryId, filters.dateFrom, filters.dateTo, filters.search, filters.storeId, retry])

  const realStoreIds = new Set(stores.filter((store) => !isDemoName(store.name)).map((store) => store.id))
  const realStoreProducts = storeProducts.filter((listing) => realStoreIds.has(listing.store_id) && !isDemoName(listing.product_name))
  const realStoreProductIds = new Set(realStoreProducts.map((listing) => listing.id))
  const arsObservations = observations.filter((item) =>
    item.currency === "ARS" && item.is_available !== false && realStoreProductIds.has(item.store_product_id),
  )
  const verifiedExchangeRates = exchangeRates.filter((item) => !isSyntheticSource(item.source))
  const excludedSyntheticRateCount = exchangeRates.length - verifiedExchangeRates.length
  const arsUsdReferenceRates = verifiedExchangeRates.filter(
    (item) => item.base_currency === "USD" && item.quote_currency === "ARS" && item.rate_side === "reference",
  )
  const parallelUsdRates = verifiedExchangeRates.filter(
    (item) => item.base_currency === "USD" && item.quote_currency === "ARS" && item.rate_type === "parallel" && item.rate_side === "sell",
  )
  const priceByDate = groupByTimestamp(arsObservations.map((item) => ({
    observed_at: item.observed_at,
    value: Number(item.amount),
  })))
  const rateByDate = groupByTimestamp(arsUsdReferenceRates.map((item) => ({
    observed_at: item.observed_at,
    value: Number(item.rate),
  })))
  const parallelByDate = groupByTimestamp(parallelUsdRates.map((item) => ({
    observed_at: item.observed_at,
    value: Number(item.rate),
  })))
  const chartData = mergeSeries(priceByDate, rateByDate, parallelByDate)
  const seriesWithData = [priceByDate.length, rateByDate.length, parallelByDate.length].filter((days) => days > 0)
  const hasInsufficientHistory = seriesWithData.some((points) => points < 2)
  const latestOfficial = [...arsUsdReferenceRates].sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))[0]
  const latestParallel = [...parallelUsdRates].sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))[0]
  const publicStores = stores.filter((store) => !isDemoName(store.name))
  const selectedStore = filters.storeId ? publicStores.find((store) => store.id === filters.storeId)?.name : null
  const selectedCategory = filters.categoryId
    ? categories.find((category) => category.id === filters.categoryId)?.name
    : null
  const loading = loadingFilters || loadingSeries

  return (
    <section className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Divisas y precios — serie temporal</h1>
          <p className="mt-1 text-sm text-slate-600">
            Compará observaciones en ARS con cotizaciones de referencia USD/ARS guardadas en PriceScope.
          </p>
        </div>
      </div>

      {(filterErrors.length > 0 || seriesErrors.length > 0) && <div role="alert" className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between"><span>{[...filterErrors, ...seriesErrors].join(" · ")}</span><button type="button" onClick={retryRequests} className="rounded-lg border border-rose-300 px-3 py-1.5 font-semibold hover:bg-rose-100">Reintentar</button></div>}

      {(observations.length >= PAGE_LIMIT ||
        exchangeRates.filter((item) => item.rate_type === "official").length >= PAGE_LIMIT ||
        exchangeRates.filter((item) => item.rate_type === "parallel").length >= PAGE_LIMIT) && !loading && (
        <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Se alcanzó el máximo de {PAGE_LIMIT.toLocaleString("es-AR")} registros por consulta. El gráfico puede omitir datos adicionales; reduce el rango de fechas o usa los filtros.
        </p>
      )}

      <FilterBar
        stores={publicStores}
        categories={categories}
        onFiltersChange={updateFilters}
        initialFilters={filters}
      />

      <Card className="border-slate-200 bg-white">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Precio vs tipo de cambio</CardTitle>
          <CardDescription className="text-xs text-slate-500">
            Observaciones por timestamp (hora local) · precio ARS · oficial y paralelo ARS por USD
            {selectedStore && ` · Tienda: ${selectedStore}`}
            {selectedCategory && ` · Categoría: ${selectedCategory}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {excludedSyntheticRateCount > 0 && !loading && (
            <p role="note" className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Se excluyeron {excludedSyntheticRateCount} cotizaciones marcadas como demo o sintéticas. La gráfica solo usa observaciones de tiendas reales y cotizaciones no sintéticas.
            </p>
          )}
          {loading ? (
            <div className="flex h-64 items-center justify-center text-sm text-slate-500" aria-live="polite">
              Cargando series de la API…
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-slate-300 text-center text-sm text-slate-500">
              No hay observaciones ni cotizaciones para este filtro.
            </div>
          ) : (
            <>
              {hasInsufficientHistory && (
                <p role="status" className="mb-3 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                  Una o más series tienen menos de dos observaciones con timestamp; no hay base suficiente para mostrar una variación temporal.
                </p>
              )}
              <DualAxisTimeSeriesChart
                data={chartData}
                title="Evolución temporal de precios y cotizaciones"
                subtitle="Puntos agrupados solo cuando comparten el mismo timestamp; sin interpolar registros"
              />
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-sm">Observaciones de precio</CardTitle></CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>Registros ARS: {loading ? "…" : arsObservations.length}</p>
            <p>Puntos temporales: {loading ? "…" : priceByDate.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Cotizaciones</CardTitle></CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>USD/ARS referencia: {loading ? "…" : arsUsdReferenceRates.length}</p>
            <p>Puntos oficiales: {loading ? "…" : rateByDate.length}</p>
            <p>Oficial USD/ARS actual: {loading ? "…" : latestOfficial ? latestOfficial.rate + " · " + latestOfficial.source + " · " + new Date(latestOfficial.observed_at).toLocaleString() : "Sin cotización disponible"}</p>
            <p>Paralelo USD/ARS actual: {loading ? "…" : latestParallel ? latestParallel.rate + " · " + latestParallel.source + " · " + new Date(latestParallel.observed_at).toLocaleString() : "Sin cotización disponible"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Rango de fechas</CardTitle></CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>{chartData.length > 0 ? `${chartData[0].date} — ${chartData[chartData.length - 1].date}` : "—"}</p>
            {loadingFilters && <p className="mt-1">Cargando filtros…</p>}
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
