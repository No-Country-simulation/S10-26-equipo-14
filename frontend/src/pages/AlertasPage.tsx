import { useEffect, useState } from "react"

import { ApiError, apiClient, type PriceAlert } from "@/lib/api"
import type { Category, Store } from "@/types"

function message(error: unknown) {
  return error instanceof ApiError || error instanceof Error ? error.message : "No se pudieron cargar las alertas."
}

export default function AlertasPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [items, setItems] = useState<PriceAlert[]>([])
  const [storeId, setStoreId] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const [rateType, setRateType] = useState<"official" | "parallel">("official")
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
    void apiClient.fetchAlerts({
      store_id: storeId ? Number(storeId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      start: start ? `${start}T00:00:00Z` : undefined,
      end: end ? `${end}T23:59:59.999Z` : undefined,
      rate_type: rateType,
      limit: 300,
    }, controller.signal).then(setItems).catch((cause: unknown) => {
      if (!(cause instanceof Error && cause.name === "AbortError")) setError(message(cause))
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [categoryId, end, rateType, start, storeId])

  return (
    <section className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Alertas de precios</h1>
        <p className="mt-1 text-sm text-slate-600">Alertas calculadas desde observaciones reales. Se requieren dos precios; la comparacion cambiaria solo aparece si hay cotizaciones alineables.</p>
      </header>
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-xs font-medium text-slate-600">Tienda<select value={storeId} onChange={(event) => setStoreId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"><option value="">Todas</option>{stores.map((store) => <option key={store.id} value={store.id}>{store.name}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">Categoria<select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"><option value="">Todas</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
        <label className="text-xs font-medium text-slate-600">Tipo de cambio<select value={rateType} onChange={(event) => setRateType(event.target.value as "official" | "parallel")} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 bg-white px-2 text-sm"><option value="official">Oficial</option><option value="parallel">Paralelo (venta)</option></select></label>
        <label className="text-xs font-medium text-slate-600">Desde<input type="date" value={start} onChange={(event) => setStart(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
        <label className="text-xs font-medium text-slate-600">Hasta<input type="date" value={end} onChange={(event) => setEnd(event.target.value)} className="mt-1 block h-10 w-full rounded-lg border border-slate-300 px-2 text-sm" /></label>
      </div>
      {error && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {loading ? <p role="status" className="text-sm text-slate-500">Calculando alertas...</p> : items.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">No hay alertas con suficiente historial y los filtros elegidos.</p>
      ) : <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white"><table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Tipo</th><th className="px-4 py-3">Producto</th><th className="px-4 py-3">Tienda</th><th className="px-4 py-3">Variacion precio</th><th className="px-4 py-3">Variacion divisa</th><th className="px-4 py-3">Observado</th><th className="px-4 py-3">Fuente</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{items.map((item) => <tr key={`${item.store_product_id}-${item.alert_type}-${item.observed_at}`}>
          <td className="px-4 py-3 font-medium text-rose-700">{item.alert_type === "price_spike" ? "Aumento >= 20%" : "Supera variacion cambiaria"}</td><td className="px-4 py-3">{item.product_name}</td><td className="px-4 py-3">{item.store_name}</td><td className="px-4 py-3 font-semibold">{Number(item.price_change_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}% ({item.previous_price} → {item.latest_price} {item.currency})</td><td className="px-4 py-3">{item.exchange_rate_change_percent === null ? "Sin cotizacion alineable" : `${Number(item.exchange_rate_change_percent).toLocaleString("es-AR", { maximumFractionDigits: 2 })}% ${item.exchange_rate_type}`}</td><td className="px-4 py-3">{new Date(item.observed_at).toLocaleString("es-AR")}</td><td className="px-4 py-3">{item.source_url ? <a className="text-indigo-700 underline" href={item.source_url} target="_blank" rel="noreferrer">Ver origen</a> : "-"}</td>
        </tr>)}</tbody>
      </table></div>}
    </section>
  )
}
