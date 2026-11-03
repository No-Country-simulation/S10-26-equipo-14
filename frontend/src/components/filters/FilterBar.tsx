import React from "react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { Store } from "@/types/store"
import type { Category } from "@/types/category"
import { ChevronLeft, Calendar, Search } from "lucide-react"

interface FilterBarProps {
  stores: Store[]
  categories: Category[]
  onFiltersChange: (filters: FilterState) => void
  initialFilters?: FilterState
}

export interface FilterState {
  storeId: number | null
  categoryId: number | null
  dateFrom: string | null
  dateTo: string | null
  search: string
}

const DEFAULT_FILTERS: FilterState = {
  storeId: null,
  categoryId: null,
  dateFrom: null,
  dateTo: null,
  search: "",
}

export default function FilterBar({
  stores,
  categories,
  onFiltersChange,
  initialFilters,
}: FilterBarProps) {
  const [filters, setFilters] = React.useState<FilterState>({
    ...DEFAULT_FILTERS,
    ...initialFilters,
  })

  const handleChange = (key: keyof FilterState, value: string | number | null) => {
    const next = { ...filters, [key]: value }
    setFilters(next)
    onFiltersChange(next)
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start sm:gap-4">
        <div className="flex flex-col gap-2 sm:flex-shrink-0">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Tienda
          </div>
          <Select
            value={filters.storeId ? String(filters.storeId) : null}
            onValueChange={(value: string | null) =>
              handleChange("storeId", value === "null" ? null : value ? Number(value) : null)
            }
          >
            <SelectTrigger className="w-[220px] sm:w-full">
              <SelectValue placeholder="Todas las tiendas">
                {filters.storeId ? stores.find((s) => s.id === filters.storeId)?.name : null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent
              className="bg-white border border-slate-200 shadow-lg z-50"
            >
              <div className="scroll-my-1 p-1">
                <div className="px-1.5 py-1 text-xs text-muted-foreground">
                  Seleccionar tienda
                </div>
                <SelectItem key="all" value="null">
                  Todas las tiendas
                </SelectItem>
                {stores.map((store) => (
                  <SelectItem key={store.id} value={String(store.id)}>
                    {store.name}
                  </SelectItem>
                ))}
              </div>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-2 sm:flex-shrink-0">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Categoría
          </div>
          <Select
            value={filters.categoryId ? String(filters.categoryId) : null}
            onValueChange={(value: string | null) =>
              handleChange("categoryId", value === "null" ? null : value ? Number(value) : null)
            }
          >
            <SelectTrigger className="w-[200px] sm:w-full">
              <SelectValue placeholder="Todas las categorías">
                {filters.categoryId ? categories.find((c) => c.id === filters.categoryId)?.name : null}
              </SelectValue>
            </SelectTrigger>
            <SelectContent
              className="bg-white border border-slate-200 shadow-lg z-50"
            >
              <div className="scroll-my-1 p-1">
                <div className="px-1.5 py-1 text-xs text-muted-foreground">
                  Seleccionar categoría
                </div>
                <SelectItem key="all" value="null">
                  Todas las categorías
                </SelectItem>
                {categories.map((category) => (
                  <SelectItem key={category.id} value={String(category.id)}>
                    {category.name}
                  </SelectItem>
                ))}
              </div>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-2 sm:flex-shrink-0">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Desde
          </div>
          <input
            type="date"
            value={filters.dateFrom ?? ""}
            onChange={(e) => handleChange("dateFrom", e.target.value || null)}
            className="w-[160px] sm:w-full h-8 rounded-lg border border-slate-300 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>
        <div className="flex flex-col gap-2 sm:flex-shrink-0">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Hasta
          </div>
          <input
            type="date"
            value={filters.dateTo ?? ""}
            onChange={(e) => handleChange("dateTo", e.target.value || null)}
            className="w-[160px] sm:w-full h-8 rounded-lg border border-slate-300 px-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div className="flex flex-col gap-2 w-full sm:w-auto sm:flex-shrink-0">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Buscar
          </div>
          <div className="relative w-full sm:w-[260px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar producto..."
              value={filters.search}
              onChange={(e) => handleChange("search", e.target.value)}
              className="w-full pl-10 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between sm:items-center sm:justify-end gap-2">
        <button
          onClick={() => {
            setFilters(DEFAULT_FILTERS)
            onFiltersChange(DEFAULT_FILTERS)
          }}
          className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors w-full sm:w-auto"
        >
          Limpiar filtros
        </button>
      </div>

      {filters.storeId || filters.categoryId || filters.dateFrom || filters.dateTo || filters.search ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {filters.storeId && (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">
              <ChevronLeft className="h-3 w-3" />
              Tienda: {stores.find((s) => s.id === filters.storeId)?.name}
            </span>
          )}
          {filters.categoryId && (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">
              <Calendar className="h-3 w-3" />
              Categoría: {categories.find((c) => c.id === filters.categoryId)?.name}
            </span>
          )}
          {filters.search && (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700">
              <Search className="h-3 w-3" />
              "{filters.search}"
            </span>
          )}
        </div>
      ) : null}
    </div>
  )
}