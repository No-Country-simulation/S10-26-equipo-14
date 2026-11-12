import { useState } from 'react'
import logo from '@/assets/logo.png'
import { Menu, Search, Bell, User, ChevronDown } from 'lucide-react'

interface TopBarProps {
  onToggleSidebar: () => void
}

export default function TopBar({ onToggleSidebar }: TopBarProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 text-slate-600 hover:bg-slate-100 rounded-lg md:hidden"
            aria-label="Abrir menú de navegación"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-3">
            <img src={logo} alt="PriceScope logo" className="h-9 w-9" />
            <div>
              <p className="text-lg font-semibold leading-none">PriceScope</p>
              <p className="mt-1 text-xs text-slate-500">
                Monitor de Inflación Real Multimoneda
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full md:max-w-md">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar productos, tiendas o categorías..."
              className="w-full pl-10 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            className="relative p-2 text-slate-600 hover:bg-slate-100 rounded-lg md:hidden"
            aria-label="Notificaciones"
          >
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500 border-2 border-white" />
          </button>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-full hover:bg-slate-200"
          >
            <User className="h-4 w-4" />
            <span className="hidden md:inline">Analista</span>
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>
      </div>

      {userMenuOpen && (
        <div
          className="absolute right-4 top-16 w-48 bg-white border border-slate-200 rounded-lg shadow-lg py-2 z-50"
          onClick={() => setUserMenuOpen(false)}
        >
          <div className="px-4 py-2 text-xs text-slate-500 border-b border-slate-100">
            analista@pricescope.com
          </div>
          <button
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
            onClick={(e) => {
              e.stopPropagation()
            }}
          >
            Perfil
          </button>
          <button
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
            onClick={(e) => {
              e.stopPropagation()
            }}
          >
            Cerrar sesión
          </button>
        </div>
      )}
    </header>
  )
}