import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import logo from '@/assets/logo.png'
import { Menu, Search } from 'lucide-react'

interface TopBarProps {
  onToggleSidebar: () => void
  sidebarOpen: boolean
}

export default function TopBar({ onToggleSidebar, sidebarOpen }: TopBarProps) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const search = query.trim()
    navigate(search ? `/catalogo?search=${encodeURIComponent(search)}` : '/catalogo')
    if (sidebarOpen) onToggleSidebar()
  }

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-3 gap-y-3 px-3 py-3 sm:px-4 md:flex-nowrap">
        <div className="flex min-w-0 flex-1 items-center gap-3 md:flex-none">
          <button
            type="button"
            onClick={onToggleSidebar}
            className="shrink-0 rounded-lg p-2 text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 md:hidden"
            aria-label={sidebarOpen ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'}
            aria-expanded={sidebarOpen}
            aria-controls="primary-navigation"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
          <div className="flex items-center gap-3">
            <img src={logo} alt="PriceScope logo" className="h-9 w-9" />
            <div>
              <p className="text-lg font-semibold leading-none">PriceScope</p>
              <p className="mt-1 hidden truncate text-xs text-slate-500 sm:block">
                Monitor de precios y cotizaciones
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={submitSearch} role="search" className="order-3 flex w-full min-w-0 md:order-0 md:ml-auto md:w-auto md:max-w-md md:flex-1">
          <label htmlFor="global-product-search" className="sr-only">Buscar productos en el catálogo</label>
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              id="global-product-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar productos en el catálogo…"
              className="h-10 w-full rounded-l-lg border border-r-0 border-slate-300 pl-10 pr-3 text-sm focus:z-10 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="inline-flex h-10 shrink-0 items-center gap-2 rounded-r-lg border border-indigo-600 bg-indigo-600 px-3 text-sm font-medium text-white hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            <Search className="h-4 w-4" aria-hidden="true" />
            <span>Buscar</span>
          </button>
        </form>
      </div>
    </header>
  )
}
