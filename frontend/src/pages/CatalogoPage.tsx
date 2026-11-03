import React from "react"

import { stores } from "@/data/mock"
import { categories } from "@/data/mock"
import { products } from "@/data/mock"
import FilterBar from "@/components/filters/FilterBar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function CatalogoPage() {
  const [filters, setFilters] = React.useState<{
    storeId: number | null
    categoryId: number | null
    search: string
  }>({ storeId: null, categoryId: null, search: "" })

  const filtered = products.filter((p) => {
    if (filters.storeId && p.store_id !== filters.storeId) return false
    if (filters.categoryId && p.category_id !== filters.categoryId) return false
    if (filters.search && !p.name.toLowerCase().includes(filters.search.toLowerCase())) return false
    return true
  })

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Catálogo de productos</h1>
          <p className="mt-1 text-sm text-slate-500">
            Explorá las publicaciones de precios por tienda y categoría.
          </p>
        </div>
      </div>

      <FilterBar
        stores={stores}
        categories={categories}
        onFiltersChange={(next) => {
          setFilters({
            storeId: next.storeId,
            categoryId: next.categoryId,
            search: next.search,
          })
        }}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((p) => (
          <Card key={p.id} className="border-slate-200 bg-white">
            <CardHeader>
              <CardTitle className="text-sm font-semibold">{p.name}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-slate-600">
              <p>Tienda: {stores.find((s) => s.id === p.store_id)?.name ?? "Desconocida"}</p>
              <p>
                Categoría: {categories.find((c) => c.id === p.category_id)?.name ?? "—"}
              </p>
              <p className="text-slate-500">{p.url}</p>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-center py-10 text-slate-500">
            No se encontraron productos con los filtros aplicados.
          </div>
        )}
      </div>
    </section>
  )
}