import { useEffect, useState } from "react"

import { ApiError, apiClient, type InflationResult, type PriceComparison, type ShrinkflationSignal } from "@/lib/api"
import type { Category, Store } from "@/types"

function message(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "No se pudieron cargar las comparativas."
}

function dateInput(daysAgo: number) {
  const date = new Date()
  date.setDate(date.getDate() - daysAgo)
  return date.toISOString().slice(0, 10)
}

function startBoundary(value: string) { return `${value}T00:00:00Z` }
function endBoundary(value: string) { return `${value}T23:59:59.999Z` }

export default function ComparativasPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [items, setItems] = useState<PriceComparison[]>([])
  const [storeId, setStoreId] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [inflation, setInflation] = useState<InflationResult | null>(null)
  const [shrinkSignals, setShrinkSignals] = useState<ShrinkflationSignal[]>([])
  const [rateType, setRateType] = useState<"official" | "parallel">("official")
  const [indicatorLoading, setIndicatorLoading] = useState(false)
  const [indicatorError, setIndicatorError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void Promise.all([
      apiClient.fetchStores(controller.signal),
      apiClient.fetchCategories(controller.signal),
    ]).then(([nextStores, nextCategories]) => {
      setStores(nextStores)
      setCategories(nextCategories)
    }).catch((cause: unknown) => {
      if (!(cause instanceof Error && cause.name === "AbortError")) setError(message(cause))
    })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    void apiClient.fetchComparisons({
      store_id: storeId ? Number(storeId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      start: start ? `${start}T00:00:00Z` : undefined,
      end: end ? `${end}T23:59:59.999Z` : undefined,
      limit: 200,
    }, controller.signal).then(setItems).catch((cause: unknown) => {
      if (!(cause instanceof Error && cause.name === "AbortError")) setError(message(cause))
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [categoryId, end, start, storeId])

  useEffect(() => {
    const controller = new AbortController()
    setIndicatorLoading(true)
    setIndicatorError(null)
    const filters = {
      store_id: storeId ? Number(storeId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      start: start ? startBoundary(start) : startBoundary(dateInput(90)),
      end: end ? endBoundary(end) : endBoundary(dateInput(0)),
    }
    void Promise.all([
      apiClient.fetchInflation({ ...filters, rate_type: rateType }, controller.signal),
      apiClient.fetchShrinkflation({ ...filters, limit: 300 }, controller.signal),
    ]).then(([nextInflation, nextSignals]) => {
      setInflation(nextInflation)
      setShrinkSignals(nextSignals)
    }).catch((cause: unknown) => {
      if (!(cause instanceof Error && cause.name === "AbortError")) setIndicatorError(message(cause))
    }).finally(() => setIndicatorLoading(false))
    return () => controller.abort()
  }, [categoryId, end, rateType, start, storeId])

  return (
    <section className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Comparativas de precios</h1>
        <p className="mt-1 text-sm text-slate-600">Ultima observacion disponible por publicacion. Solo compara monedas iguales y productos canonicos compartidos.</p>
      </header>
      <section className="space-y-4 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="font-semibold text-slate-900">Inflación acumulada y reduflación</h2>
            <p className="mt-1 text-xs text-slate-600">Período: {start || dateInput(90)} a {end || dateInput(0)}. Mismos productos/publicaciones y monedas; promedio equiponderado.</p></div>
          <label className="text-xs font-medium text-slate-600">Cotización para comparar variación cambiaria
            <select value={rateType} onChange={(event) => setRateType(event.target.value as "official" | "parallel")} className="mt-1 block h-9 rounded-lg border border-slate-300 bg-white px-2"><option value="official">Oficial</option><option value="parallel">Paralela (venta)</option></select>
          </label>
        </div>
        {indicatorError && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{indicatorError}</p>}
        {indicatorLoading ? <p role="status" className="text-sm text-slate-500">Calculando indicadores...</p> : <>
          {inflation?.status === "insufficient_data" && <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{inflation.message} No se estiman valores faltantes.</p>}
          {inflation?.currencies.map((row) => <div key={row.currency} className="grid gap-2 rounded-lg bg-white p-3 text-sm sm:grid-cols-3">
            <p><span className="text-slate-500">Inflación de precios ({row.currency})</span><br/><strong>{Number(row.inflation_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}%</strong> · {row.products_count} productos</p>
            <p><span className="text-slate-500">Variación cambiaria {row.fx_rate_type ?? ""}</span><br/><strong>{row.fx_variation_percent === null ? "Sin datos alineables" : `${Number(row.fx_variation_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}%`}</strong></p>
            <p><span className="text-slate-500">Diferencia precio − divisa</span><br/><strong>{row.price_minus_fx_percentage_points === null ? "No disponible" : `${Number(row.price_minus_fx_percentage_points).toLocaleString("es-AR", { maximumFractionDigits: 2 })} puntos porcentuales`}</strong></p>
          </div>)}
          {!!inflation?.products.length && <details className="rounded-lg bg-white p-3 text-sm"><summary className="cursor-pointer font-medium">Variación por producto</summary><ul className="mt-2 space-y-2">{inflation.products.map((row) => <li key={`${row.product_id}-${row.currency}`}><div className="flex justify-between gap-3"><span>{row.product_name} · {row.currency} · {row.listings_count} publicaciones</span><strong>{Number(row.inflation_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}%</strong></div><ul className="ml-4 text-xs text-slate-500">{row.listings.map((listing) => <li key={listing.store_product_id}>{listing.initial_price} ({new Date(listing.initial_observed_at).toLocaleDateString("es-AR")}) → {listing.final_price} ({new Date(listing.final_observed_at).toLocaleDateString("es-AR")})</li>)}</ul></li>)}</ul></details>}
          <div className="rounded-lg bg-white p-3">
            <h3 className="text-sm font-semibold">Señales de reduflación</h3>
            <p className="mb-2 text-xs text-slate-500">Solo observaciones con cantidad de presentación registrada en cada fecha, del mismo producto y publicación; unidades normalizadas a g, ml o unidad.</p>
            {shrinkSignals.length === 0 ? <p className="text-sm text-slate-500">Sin señales verificables en este período. La cantidad faltante no se infiere.</p> : <ul className="space-y-2">{shrinkSignals.map((signal) => <li key={`${signal.store_product_id}-${signal.observed_at}`} className="text-sm"><strong>{signal.status === "confirmed" ? "Confirmada" : "Posible"}</strong> · {signal.product_name} ({signal.store_name}): {signal.previous_quantity} → {signal.latest_quantity} {signal.unit}; precio unitario {Number(signal.unit_price_change_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}% ({signal.currency}). <span className="text-xs text-slate-500">{new Date(signal.observed_at).toLocaleDateString("es-AR")}</span></li>)}</ul>}
          </div>
        </>}
      </section>
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-xs font-medium text-slate-600">Tienda incluida
          <select value={storeId} onChange={(event) => setStoreId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm">
            <option value="">Todas las tiendas</option>{stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-600">Categoria
          <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm">
            <option value="">Todas</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
        </label>
        <label className="text-xs font-medium text-slate-600">Desde<input type="date" value={start} onChange={(event) => setStart(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
        <label className="text-xs font-medium text-slate-600">Hasta<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
      </div>
      {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {loading ? <p role="status" className="text-sm text-slate-500">Cargando comparativas...</p> : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No hay productos con precios comparables entre dos o mas tiendas para estos filtros.</p>
      ) : items.map((item) => (
        <article key={item.product_id} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 p-4">
            <h2 className="font-semibold text-slate-900">{item.product_name}</h2>
            <span className="text-sm font-medium text-slate-700">Brecha {Number(item.spread_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}% ({item.spread_amount} {item.currency})</span>
          </div>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Tienda</th><th className="px-4 py-3">Precio</th><th className="px-4 py-3">Promocion</th><th className="px-4 py-3">Precio efectivo</th><th className="px-4 py-3">Fecha</th><th className="px-4 py-3">Origen</th></tr></thead>
            <tbody className="divide-y divide-slate-100">{item.prices.map((price) => <tr key={price.store_product_id}>
              <td className="px-4 py-3 font-medium text-slate-800">{price.store_name}</td><td className="px-4 py-3">{price.amount} {price.currency}</td><td className="px-4 py-3">{price.promotional_price ? `${price.promotional_price} ${price.currency}` : "-"}</td><td className="px-4 py-3 font-semibold">{price.effective_price} {price.currency}</td><td className="px-4 py-3">{new Date(price.observed_at).toLocaleString("es-AR")}</td><td className="px-4 py-3">{price.source_url ? <a className="text-indigo-700 underline" href={price.source_url} target="_blank" rel="noreferrer">Ver fuente</a> : "-"}</td>
            </tr>)}</tbody>
          </table></div>
        </article>
      ))}
    </section>
  )
}
