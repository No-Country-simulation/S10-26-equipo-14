import React from 'react'
import { prices } from '@/data/mock'
import { exchangeRates } from '@/data/mock'
import { stores } from '@/data/mock'
import { categories } from '@/data/mock'
import { products } from '@/data/mock'
import DualAxisTimeSeriesChart from '@/components/charts/DualAxisTimeSeriesChart'
import FilterBar from '@/components/filters/FilterBar'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type RawPrice = {
  id: number
  product_id: number
  store_id: number
  amount: number | string
  currency: string
  observed_at: string
}

type RawRate = {
  id: number
  rate: number | string
  source: string
  recorded_at: string
}

function groupByDate(items: { observed_at: string; value: number }[]) {
  const grouped = new Map<string, number>()
  for (const item of items) {
    const day = item.observed_at.split('T')[0]
    const prev = grouped.get(day) ?? 0
    grouped.set(day, prev + item.value)
  }
  return Array.from(grouped.entries()).map(([date, value]) => ({
    date,
    value,
  }))
}

function mergeSeries(
  priceByDate: { date: string; value: number }[],
  rateByDate: { date: string; value: number }[]
) {
  const allDates = new Set([...priceByDate.map((d) => d.date), ...rateByDate.map((d) => d.date)])
  const priceMap = new Map(priceByDate.map((d) => [d.date, d.value]))
  const rateMap = new Map(rateByDate.map((d) => [d.date, d.value]))

  return Array.from(allDates)
    .sort()
    .map((date) => ({
      date,
      price: priceMap.get(date) ?? null,
      rate: rateMap.get(date) ?? null,
    }))
}

export default function DivisasPage() {
  const [filters, setFilters] = React.useState<{
    storeId: number | null
    categoryId: number | null
    dateFrom: string | null
    dateTo: string | null
  }>({ storeId: null, categoryId: null, dateFrom: null, dateTo: null })

  // Mapa producto_id -> category_id para filtrar precios por categoría
  const productCategoryMap = new Map(products.map((p) => [p.id, p.category_id]))

  // Filtrar precios por tienda, categoría y rango de fechas
  let filteredPrices = prices as unknown as RawPrice[]
  if (filters.storeId) {
    filteredPrices = filteredPrices.filter((p) => p.store_id === filters.storeId)
  }
  if (filters.categoryId) {
    filteredPrices = filteredPrices.filter(
      (p) => productCategoryMap.get(p.product_id) === filters.categoryId
    )
  }
  if (filters.dateFrom) {
    filteredPrices = filteredPrices.filter((p) => p.observed_at >= filters.dateFrom + 'T00:00:00Z')
  }
  if (filters.dateTo) {
    filteredPrices = filteredPrices.filter((p) => p.observed_at <= filters.dateTo + 'T23:59:59Z')
  }

  // Filtrar tipos de cambio por rango de fechas
  let filteredRates = exchangeRates as unknown as RawRate[]
  if (filters.dateFrom) {
    filteredRates = filteredRates.filter((r) => r.recorded_at >= filters.dateFrom + 'T00:00:00Z')
  }
  if (filters.dateTo) {
    filteredRates = filteredRates.filter((r) => r.recorded_at <= filters.dateTo + 'T23:59:59Z')
  }

  // Agregar precios por fecha (promedio simple por día)
  const priceByDate = groupByDate(
    filteredPrices.map((p) => ({ observed_at: p.observed_at, value: Number(p.amount) }))
  )

  // Agregar tipos de cambio por fecha (promedio simple por día)
  const rateByDate = groupByDate(
    filteredRates.map((r) => ({ observed_at: r.recorded_at, value: Number(r.rate) }))
  )

  const chartData = mergeSeries(priceByDate, rateByDate)

  const selectedStore = filters.storeId ? stores.find((s) => s.id === filters.storeId)?.name : null
  const selectedCategory = filters.categoryId
    ? categories.find((c) => c.id === filters.categoryId)?.name
    : null

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Divisas y precios — serie temporal</h1>
          <p className="mt-1 text-sm text-slate-600">
            Compará la evolución de los precios (ARS) con el tipo de cambio (ARS/USD) en un mismo
            eje de tiempo.
          </p>
        </div>
      </div>

      <FilterBar
        stores={stores}
        categories={categories}
        onFiltersChange={(next) => setFilters(next)}
        initialFilters={{
          storeId: filters.storeId,
          categoryId: filters.categoryId,
          dateFrom: filters.dateFrom,
          dateTo: filters.dateTo,
          search: '',
        }}
      />

      <Card className="border-slate-200 bg-white">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Precio vs tipo de cambio</CardTitle>
          <CardDescription className="text-xs text-slate-500">
            Eje izquierdo: precio promedio en ARS · Eje derecho: tipo de cambio en ARS por USD
            {selectedStore && ` · Tienda: ${selectedStore}`}
            {selectedCategory && ` · Categoría: ${selectedCategory}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DualAxisTimeSeriesChart
            data={chartData}
            title="Evolución diaria de precios y tipo de cambio"
            subtitle="Datos de mock — fuente: precios y cotizaciones del catálogo"
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Observaciones de precio</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>Registros filtrados: {filteredPrices.length}</p>
            <p>Días con datos: {priceByDate.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cotizaciones</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>Registros filtrados: {filteredRates.length}</p>
            <p>Días con datos: {rateByDate.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Rango de fechas</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-slate-600">
            <p>{chartData.length > 0 ? chartData[0].date : '—'} — {chartData.length > 0 ? chartData[chartData.length - 1].date : '—'}</p>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}