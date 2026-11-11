import React from "react"

import DualAxisTimeSeriesChart from "@/components/charts/DualAxisTimeSeriesChart"
import FilterBar, { type FilterState } from "@/components/filters/FilterBar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ApiError, apiClient } from "@/lib/api"
import type { Category, ExchangeRate, PriceObservation, Store } from "@/types"

const PAGE_LIMIT = 1000

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return "No se pudieron cargar las observaciones de PriceScope."
}

function groupByDate(items: { observed_at: string; value: number }[]) {
  const grouped = new Map<string, { total: number; count: number }>()
  for (const item of items) {
    const day = item.observed_at.slice(0, 10)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || !Number.isFinite(item.value)) continue
    const current = grouped.get(day) ?? { total: 0, count: 0 }
    grouped.set(day, { total: current.total + item.value, count: current.count + 1 })
  }
  return Array.from(grouped.entries()).sort(([left], [right]) => left.localeCompare(right)).map(([date, data]) => ({
    date,
    value: data.total / data.count,
  }))
}

function mergeSeries(
  priceByDate: { date: string; value: number }[],
  rateByDate: { date: string; value: number }[],
) {
  const allDates = new Set([...priceByDate.map((item) => item.date), ...rateByDate.map((item) => item.date)])
  const priceMap = new Map(priceByDate.map((item) => [item.date, item.value]))
  const rateMap = new Map(rateByDate.map((item) => [item.date, item.value]))
  return Array.from(allDates).sort().map((date) => ({
    date,
    price: priceMap.get(date) ?? null,
    rate: rateMap.get(date) ?? null,
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
  const [categories, setCategories] = React.useState<Category[]>([])
  const [observations, setObservations] = React.useState<PriceObservation[]>([])
  const [exchangeRates, setExchangeRates] = React.useState<ExchangeRate[]>([])
  const [loadingFilters, setLoadingFilters] = React.useState(true)
  const [loadingSeries, setLoadingSeries] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [retry, setRetry] = React.useState(0)

  const retryRequests = () => {
    setError(null)
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
    void Promise.all([
      apiClient.fetchStores(controller.signal),
      apiClient.fetchCategories(controller.signal),
    ])
      .then(([loadedStores, loadedCategories]) => {
        if (!active) return
        setStores(loadedStores)
        setCategories(loadedCategories)
        setError(null)
      })
      .catch((cause: unknown) => {
        if (active && !(cause instanceof Error && cause.name === "AbortError")) {
          setError(errorMessage(cause))
        }
      })
      .finally(() => {
        if (active) setLoadingFilters(false)
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [retry])

  React.useEffect(() => {
    const controller = new AbortController()
    let active = true
    const query = {
      store_id: filters.storeId ?? undefined,
      category_id: filters.categoryId ?? undefined,
      start: dateBoundary(filters.dateFrom),
      end: dateBoundary(filters.dateTo, true),
      search: filters.search.trim() || undefined,
      limit: PAGE_LIMIT,
    }
    void Promise.all([
      apiClient.fetchPriceObservations(query, controller.signal),
      apiClient.fetchExchangeRates({ start: query.start, end: query.end, limit: PAGE_LIMIT }, controller.signal),
    ])
      .then(([loadedObservations, loadedRates]) => {
        if (!active) return
        setObservations(loadedObservations)
        setExchangeRates(loadedRates)
        setError(null)
      })
      .catch((cause: unknown) => {
        if (!active || (cause instanceof Error && cause.name === "AbortError")) return
        setObservations([])
        setExchangeRates([])
        setError(errorMessage(cause))
      })
      .finally(() => {
        if (active) setLoadingSeries(false)
      })
    return () => {
      active = false
      controller.abort()
    }
  }, [filters.categoryId, filters.dateFrom, filters.dateTo, filters.search, filters.storeId, retry])

  const arsObservations = observations.filter((item) => item.currency === "ARS")
  const arsUsdReferenceRates = exchangeRates.filter(
    (item) => item.base_currency === "USD" && item.quote_currency === "ARS" && item.rate_side === "reference",
  )
  const priceByDate = groupByDate(arsObservations.map((item) => ({
    observed_at: item.observed_at,
    value: Number(item.amount),
  })))
  const rateByDate = groupByDate(arsUsdReferenceRates.map((item) => ({
    observed_at: item.observed_at,
    value: Number(item.rate),
  })))
  const chartData = mergeSeries(priceByDate, rateByDate)
  const hasSyntheticRates = arsUsdReferenceRates.some((item) => /demo|sint[eé]tic|synthetic/i.test(item.source))
  const seriesWithData = [priceByDate.length, rateByDate.length].filter((days) => days > 0)
  const hasInsufficientHistory = seriesWithData.some((days) => days < 2)
  const selectedStore = filters.storeId ? stores.find((store) => store.id === filters.storeId)?.name : null
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

      {error && (
        <div role="alert" className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 sm:flex-row sm:items-center sm:justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={retryRequests}
            className="rounded-lg border border-rose-300 px-3 py-1.5 font-semibold hover:bg-rose-100"
          >
            Reintentar
          </button>
        </div>
      )}

      {(observations.length >= PAGE_LIMIT || exchangeRates.length >= PAGE_LIMIT) && !loading && (
        <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Se alcanzó el máximo de {PAGE_LIMIT.toLocaleString("es-AR")} registros por consulta. El gráfico puede omitir datos adicionales; reduce el rango de fechas o usa los filtros.
        </p>
      )}

      <FilterBar
        stores={stores}
        categories={categories}
        onFiltersChange={updateFilters}
        initialFilters={filters}
      />

      <Card className="border-slate-200 bg-white">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Precio vs tipo de cambio</CardTitle>
          <CardDescription className="text-xs text-slate-500">
            Precio promedio diario (ARS) · cotización de referencia promedio (ARS por USD)
            {selectedStore && ` · Tienda: ${selectedStore}`}
            {selectedCategory && ` · Categoría: ${selectedCategory}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {hasSyntheticRates && !loading && (
            <p role="note" className="mb-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Las cotizaciones mostradas son datos sintéticos de demostración; no representan valores reales.
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
                  Una o más series tienen datos de menos de dos días; sus puntos no muestran una evolución temporal.
                </p>
              )}
              <DualAxisTimeSeriesChart
                data={chartData}
                title="Evolución diaria de precios y tipo de cambio"
                subtitle="Promedios diarios calculados a partir de los registros recibidos desde la API"
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
            <p>Días con datos: {loading ? "…" : priceByDate.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Cotizaciones</CardTitle></CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>USD/ARS referencia: {loading ? "…" : arsUsdReferenceRates.length}</p>
            <p>Días con datos: {loading ? "…" : rateByDate.length}</p>
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
