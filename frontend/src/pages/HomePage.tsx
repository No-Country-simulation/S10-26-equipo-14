import { useEffect, useState } from "react"

import MetricCard from "@/components/metrics/MetricCard"
import { ApiError, apiClient } from "@/lib/api"

type Resource = "stores" | "categories" | "products" | "rates"
type DashboardErrors = Record<Resource, string | null>
type DashboardLoading = Record<Resource, boolean>

interface DashboardData {
  stores: Awaited<ReturnType<typeof apiClient.fetchManagedStores>>
  categories: Awaited<ReturnType<typeof apiClient.fetchCategories>>
  productTotal: number | null
  rates: Awaited<ReturnType<typeof apiClient.fetchExchangeRates>>
}

const labels: Record<Resource, string> = {
  stores: "tiendas",
  categories: "categorías",
  products: "productos",
  rates: "cotizaciones",
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return "No se pudo cargar este recurso de PriceScope."
}

function formatRate(rate: DashboardData["rates"][number] | undefined): string {
  if (!rate) return "—"
  return `${rate.base_currency}/${rate.quote_currency} ${Number(rate.rate).toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export default function HomePage() {
  const [data, setData] = useState<DashboardData>({ stores: [], categories: [], productTotal: null, rates: [] })
  const [loading, setLoading] = useState<DashboardLoading>({ stores: true, categories: true, products: true, rates: true })
  const [errors, setErrors] = useState<DashboardErrors>({ stores: null, categories: null, products: null, rates: null })
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    const load = <T,>(resource: Resource, request: Promise<T>, save: (value: T) => void) => {
      setLoading((current) => ({ ...current, [resource]: true }))
      setErrors((current) => ({ ...current, [resource]: null }))
      void request
        .then((value) => {
          if (!active) return
          save(value)
        })
        .catch((cause: unknown) => {
          if (active && !(cause instanceof Error && cause.name === "AbortError")) {
            setErrors((current) => ({ ...current, [resource]: errorMessage(cause) }))
          }
        })
        .finally(() => {
          if (active) setLoading((current) => ({ ...current, [resource]: false }))
        })
    }

    load("stores", apiClient.fetchManagedStores(controller.signal), (stores) =>
      setData((current) => ({ ...current, stores })),
    )
    load("categories", apiClient.fetchCategories(controller.signal), (categories) =>
      setData((current) => ({ ...current, categories })),
    )
    load("products", apiClient.fetchProductsWithPrices({ limit: 100, offset: 0 }, controller.signal), (products) =>
      setData((current) => ({
        ...current,
        productTotal: products.items.filter((product) => product.latest_price !== null).length,
      })),
    )
    load("rates", apiClient.fetchExchangeRates({ limit: 100 }, controller.signal), (rates) =>
      setData((current) => ({ ...current, rates })),
    )

    return () => {
      active = false
      controller.abort()
    }
  }, [retry])

  const latestRate = data.rates.reduce<DashboardData["rates"][number] | undefined>(
    (latest, rate) => !latest || Date.parse(rate.observed_at) > Date.parse(latest.observed_at) ? rate : latest,
    undefined,
  )
  const failedResources = (Object.keys(errors) as Resource[]).filter((resource) => errors[resource])

  return (
    <section>
      <div className="mx-auto max-w-3xl text-center">
        <p className="mb-4 inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Fase inicial — MVP en desarrollo
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">PriceScope</h1>
        <p className="mt-4 text-lg text-slate-600">
          Consulta productos, tiendas, observaciones históricas y cotizaciones cambiarias. Explora los registros disponibles y su evolución en las herramientas del MVP.
        </p>
      </div>

      {failedResources.length > 0 && (
        <div role="alert" className="mx-auto mt-8 max-w-3xl rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
          <p className="font-semibold">No se pudieron cargar algunos recursos:</p>
          <ul className="mt-2 list-inside list-disc">
            {failedResources.map((resource) => <li key={resource}>{labels[resource]}: {errors[resource]}</li>)}
          </ul>
          <button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-3 rounded-lg border border-rose-300 px-3 py-1.5 font-semibold hover:bg-rose-100">
            Reintentar recursos con error
          </button>
        </div>
      )}

      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Tiendas con extracción" value={loading.stores ? "…" : errors.stores ? "Error" : data.stores.filter((store) => store.is_active && store.last_extraction_status === "SUCCESS").length} subtitle={loading.stores ? "Cargando" : errors.stores ? "No disponible" : "con última ejecución exitosa"} />
        <MetricCard title="Productos en catálogo" value={loading.products ? "…" : errors.products ? "Error" : data.productTotal ?? 0} subtitle={loading.products ? "Cargando" : errors.products ? "No disponible" : "registrados en la API"} />
        <MetricCard title="Categorías" value={loading.categories ? "…" : errors.categories ? "Error" : data.categories.length} subtitle={loading.categories ? "Cargando" : errors.categories ? "No disponible" : "registradas en la API"} />
        <MetricCard title="Última cotización" value={loading.rates ? "…" : errors.rates ? "Error" : formatRate(latestRate)} subtitle={loading.rates ? "Cargando" : errors.rates ? "No disponible" : latestRate ? `${latestRate.rate_type} · ${latestRate.source} · ${new Date(latestRate.observed_at).toLocaleDateString("es-AR")}` : "sin datos de cotización"} />
      </div>
    </section>
  )
}
