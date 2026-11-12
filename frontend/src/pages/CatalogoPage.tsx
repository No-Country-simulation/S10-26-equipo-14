import React from "react"
import { useSearchParams } from "react-router-dom"

import FilterBar, { type FilterState } from "@/components/filters/FilterBar"
import CatalogProductSummary, { CatalogPresentation } from "@/components/catalog/CatalogProductSummary"
import { apiClient, ApiError } from "@/lib/api"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { Category, PricedProduct } from "@/types"

interface CatalogPageProps {
  initialCategoryId?: number | null
}

const PAGE_SIZE = 20

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return "Ocurrió un error inesperado al consultar PriceScope API."
}

function dateBoundary(value: string | null, endOfDay = false) {
  if (!value) return undefined
  return `${value}T${endOfDay ? "23:59:59.999" : "00:00:00"}Z`
}

export default function CatalogoPage({
  initialCategoryId = null,
}: CatalogPageProps) {
  const [searchParams] = useSearchParams()
  const routeSearch = searchParams.get("search")?.trim() ?? ""
  const [products, setProducts] = React.useState<PricedProduct[]>([])
  const [total, setTotal] = React.useState(0)
  const [categoriesList, setCategoriesList] = React.useState<Category[]>([])
  const [filters, setFilters] = React.useState<FilterState>({
    storeId: null,
    categoryId: initialCategoryId,
    dateFrom: null,
    dateTo: null,
    search: routeSearch,
  })
  const normalizedSearch = filters.search.trim()
  const lastFetchedSearch = React.useRef(normalizedSearch)
  const [offset, setOffset] = React.useState(0)
  const [productsLoading, setProductsLoading] = React.useState(true)
  const [productsError, setProductsError] = React.useState<string | null>(null)
  const [categoriesLoading, setCategoriesLoading] = React.useState(true)
  const [categoriesError, setCategoriesError] = React.useState<string | null>(null)
  const [productsRetry, setProductsRetry] = React.useState(0)
  const [categoriesRetry, setCategoriesRetry] = React.useState(0)

  React.useEffect(() => {
    const controller = new AbortController()
    let active = true
    const debounceMs = normalizedSearch === lastFetchedSearch.current ? 0 : 300

    const timeoutId = window.setTimeout(() => {
      lastFetchedSearch.current = normalizedSearch
      void apiClient
        .fetchProductsWithPrices(
          {
            limit: PAGE_SIZE,
            offset,
            category_id: filters.categoryId,
            search: normalizedSearch || undefined,
            start: dateBoundary(filters.dateFrom),
            end: dateBoundary(filters.dateTo, true),
          },
          controller.signal
        )
        .then((page) => {
          if (!active) return
          setProducts(page.items)
          setTotal(page.total)
        })
        .catch((error: unknown) => {
          if (!active || (error instanceof Error && error.name === "AbortError")) return
          setProducts([])
          setTotal(0)
          setProductsError(errorMessage(error))
        })
        .finally(() => {
          if (active) setProductsLoading(false)
        })
    }, debounceMs)

    return () => {
      active = false
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [filters.categoryId, filters.dateFrom, filters.dateTo, normalizedSearch, offset, productsRetry])

  React.useEffect(() => {
    const controller = new AbortController()
    let active = true

    apiClient
      .fetchCategories(controller.signal)
      .then((result) => {
        if (active) setCategoriesList(result)
      })
      .catch((error: unknown) => {
        if (!active || (error instanceof Error && error.name === "AbortError")) return
        setCategoriesList([])
        setCategoriesError(errorMessage(error))
      })
      .finally(() => {
        if (active) setCategoriesLoading(false)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [categoriesRetry])

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const categoryName = (categoryId: number | null) => {
    if (categoryId === null) return "—"
    return categoriesList.find((category) => category.id === categoryId)?.name ?? "—"
  }

  const handleFiltersChange = (next: FilterState) => {
    setFilters(next)
    const changed = next.categoryId !== filters.categoryId ||
      next.search !== filters.search ||
      next.dateFrom !== filters.dateFrom ||
      next.dateTo !== filters.dateTo
    if (changed) {
      setProductsLoading(true)
      setProductsError(null)
      setOffset(0)
    }
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
        categories={categoriesList}
        showStoreFilter={false}
        onFiltersChange={handleFiltersChange}
        initialFilters={{
          storeId: null,
          categoryId: filters.categoryId,
          dateFrom: filters.dateFrom,
          dateTo: filters.dateTo,
          search: filters.search,
        }}
      />

      {categoriesLoading && (
        <p className="text-sm text-slate-500" role="status">Cargando categorías…</p>
      )}
      {categoriesError && (
        <div className="flex items-center justify-between gap-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="alert">
          <span>No se pudieron cargar las categorías: {categoriesError}</span>
          <button
            type="button"
            onClick={() => {
              setCategoriesLoading(true)
              setCategoriesError(null)
              setCategoriesRetry((retry) => retry + 1)
            }}
            className="shrink-0 font-medium underline"
          >
            Reintentar
          </button>
        </div>
      )}

      {productsError && (
        <div className="flex items-center justify-between gap-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
          <span>No se pudieron cargar los productos: {productsError}</span>
          <button
            type="button"
            onClick={() => {
              setProductsLoading(true)
              setProductsError(null)
              setProductsRetry((retry) => retry + 1)
            }}
            className="shrink-0 font-medium underline"
          >
            Reintentar
          </button>
        </div>
      )}

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
              <TableHead className="min-w-56">Presentación</TableHead>
              <TableHead className="min-w-64">Último precio observado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {productsLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-slate-500" role="status">
                  Cargando productos…
                </TableCell>
              </TableRow>
            ) : productsError ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-slate-500">
                  No se muestran datos hasta poder conectar con la API.
                </TableCell>
              </TableRow>
            ) : products.length > 0 ? (
              products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-mono text-slate-500">{product.id}</TableCell>
                  <TableCell className="font-medium">{product.name}</TableCell>
                  <TableCell>
                    {product.brand ?? <span className="text-slate-400">—</span>}
                  </TableCell>
                  <TableCell>
                    {product.model ?? <span className="text-slate-400">—</span>}
                  </TableCell>
                  <TableCell>
                    {product.barcode ?? <span className="text-slate-400">—</span>}
                  </TableCell>
                  <TableCell>{categoryName(product.category_id)}</TableCell>
                  <TableCell><CatalogPresentation product={product} /></TableCell>
                  <TableCell><CatalogProductSummary product={product} /></TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-slate-500">
                  {filters.search
                    ? "No se encontraron productos que coincidan con la búsqueda y los filtros."
                    : "No se encontraron productos con los filtros aplicados."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {!productsLoading && !productsError && total > 0 && (
          <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <div>
              Mostrando <b>{products.length}</b> resultado(s) de esta página · <b>{total}</b> coincidencias
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => {
                  setProductsLoading(true)
                  setProductsError(null)
                  setOffset(Math.max(0, offset - PAGE_SIZE))
                }}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="px-2">Página {currentPage} de {totalPages}</span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => {
                  setProductsLoading(true)
                  setProductsError(null)
                  setOffset(offset + PAGE_SIZE)
                }}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>
      {(filters.dateFrom || filters.dateTo) && (
        <p className="text-xs text-slate-500">
          El rango de fechas se aplica a las observaciones de precio disponibles.
        </p>
      )}
      {categoriesLoading && <span className="sr-only">Cargando opciones de categorías</span>}
    </section>
  )
}
