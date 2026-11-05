import type { Category, Product } from "@/types"

/** URL base de la API de PriceScope. En desarrollo, Vite proxyea /api al backend. */
const API_BASE = import.meta.env.VITE_API_URL ?? "/api"

type ApiError = { status: number; message: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error: ApiError = {
      status: response.status,
      message: body?.detail ?? `Error ${response.status} al consultar ${path}`,
    }
    throw error
  }

  return (await response.json()) as T
}

export interface PaginatedProducts {
  items: Product[]
  total: number
  limit: number
  offset: number
}

export interface ApiClient {
  fetchProducts: (
    params?: {
      category_id?: number | null
      limit?: number
      offset?: number
    },
    signal?: AbortSignal
  ) => Promise<PaginatedProducts>
  fetchCategories: (signal?: AbortSignal) => Promise<Category[]>
}

/** Cliente de API para el catálogo canónico. */
export const apiClient: ApiClient = {
  fetchProducts: async (params, signal) => {
    const searchParams = new URLSearchParams()
    if (params?.category_id != null) {
      searchParams.set("category_id", String(params.category_id))
    }
    if (params?.limit != null) {
      searchParams.set("limit", String(params.limit))
    }
    if (params?.offset != null) {
      searchParams.set("offset", String(params.offset))
    }
    const path = `/api/v1/products/paginated?${searchParams.toString()}`
    return request<PaginatedProducts>(path, { signal })
  },

  fetchCategories: async (signal) => {
    return request<Category[]>(`/api/v1/categories`, { signal })
  },
}