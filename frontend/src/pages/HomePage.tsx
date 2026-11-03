import { stores } from "@/data/mock"
import { categories } from "@/data/mock"
import { products } from "@/data/mock"
import { exchangeRates } from "@/data/mock"
import MetricCard from "@/components/metrics/MetricCard"

const activeStores = stores.filter((s) => s.is_active).length
const totalProducts = products.length
const totalCategories = categories.length
const officialRate = exchangeRates.find(
  (r) => r.source === "oficial",
)

export default function HomePage() {
  return (
    <section>
      <div className="mx-auto max-w-3xl text-center">
        <p className="mb-4 inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Fase inicial — MVP en desarrollo
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          PriceScope
        </h1>
        <p className="mt-4 text-lg text-slate-600">
          Monitoreá precios de productos en diferentes tiendas, comparalos entre
          monedas y analizá la inflación real con indicadores y visualizaciones
          interactivas.
        </p>
      </div>

      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Tiendas activas"
          value={activeStores}
          subtitle={`de ${stores.length} registradas`}
          trend={{ label: "vs total", value: stores.length, positive: true }}
        />
        <MetricCard
          title="Productos monitoreados"
          value={totalProducts}
          subtitle="en el catálogo actual"
        />
        <MetricCard
          title="Categorías"
          value={totalCategories}
          subtitle="para clasificar publicaciones"
        />
        <MetricCard
          title="Dólar oficial"
          value={officialRate ? `$ ${Number(officialRate.rate).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
          subtitle={officialRate ? new Date(officialRate.recorded_at).toLocaleDateString("es-AR") : "sin datos"}
        />
      </div>
    </section>
  )
}
