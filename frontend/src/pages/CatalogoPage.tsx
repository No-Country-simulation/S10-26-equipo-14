import React from "react"

import { canonicalProducts, categories } from "@/data/mock"
import FilterBar from "@/components/filters/FilterBar"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { Category, Product } from "@/types"

interface CatalogPageProps {
  initialCategoryId?: number | null
}

export default function CatalogoPage({
  initialCategoryId = null,
}: CatalogPageProps) {
  const [products] = React.useState<Product[]>(canonicalProducts)
  const [categoriesList] = React.useState<Category[]>(categories)
  const [filters, setFilters] = React.useState<{
    categoryId: number | null
    search: string
  }>({ categoryId: initialCategoryId, search: "" })
  const [limit] = React.useState(20)
  const [offset, setOffset] = React.useState(0)

  const filtered = products.filter((p) => {
    if (filters.categoryId && p.category_id !== filters.categoryId) return false
    if (filters.search && !p.name.toLowerCase().includes(filters.search.toLowerCase()))
      return false
    return true
  })

  const total = filtered.length
  const totalPages = Math.ceil(total / limit) || 1
  const currentPage = Math.floor(offset / limit) + 1
  const paginated = filtered.slice(offset, offset + limit)

  const categoryName = (categoryId: number | null) => {
    if (!categoryId) return "—"
    return categoriesList.find((c) => c.id === categoryId)?.name ?? "—"
  }

  return (
    <section className="mx-auto max-w-7xl px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Catálogo canónico</h1>
          <p className="mt-1 text-sm text-slate-500">
            Explorá los productos del catálogo compartido entre comercios.
          </p>
        </div>
      </div>

      <FilterBar
        stores={[]}
        categories={categories}
        showStoreFilter={false}
        onFiltersChange={(next) => {
          setFilters({
            categoryId: next.categoryId,
            search: next.search,
          })
          setOffset(0)
        }}
        initialFilters={{
          storeId: null,
          categoryId: filters.categoryId,
          dateFrom: null,
          dateTo: null,
          search: filters.search,
        }}
      />

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <Table className="w-full text-sm">
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">ID</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead className="w-48">Marca</TableHead>
              <TableHead className="w-48">Modelo</TableHead>
              <TableHead className="w-48">Código de barras</TableHead>
              <TableHead className="w-48">Categoría</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginated.length > 0 ? (
              paginated.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-mono text-slate-500">
                    {product.id}
                  </TableCell>
                  <TableCell className="font-medium">{product.name}</TableCell>
                  <TableCell>
                    {product.brand ?? (
                      <span className="text-slate-400">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {product.model ?? (
                      <span className="text-slate-400">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {product.barcode ?? (
                      <span className="text-slate-400">—</span>
                    )}
                  </TableCell>
                  <TableCell>{categoryName(product.category_id)}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-slate-500">
                  No se encontraron productos con los filtros aplicados.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {total > 0 && (
          <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 flex items-center justify-between text-sm text-slate-600">
            <div>
              Mostrando <b>{offset + 1}</b> a{" "}
              <b>{Math.min(offset + paginated.length, total)}</b> de <b>{total}</b>
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage === 1}
                onClick={() => setOffset(Math.max(0, offset - limit))}
                className="px-3 py-1.5 text-sm border border-slate-300 rounded-md hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Anterior
              </button>
              <span className="px-2">
                Página {currentPage} de {totalPages}
              </span>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setOffset(offset + limit)}
                className="px-3 py-1.5 text-sm border border-slate-300 rounded-md hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
