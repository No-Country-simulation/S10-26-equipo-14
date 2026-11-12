import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Package,
  Scale,
  DollarSign,
  Bell,
  Info,
  Monitor,
  X,
  Store,
} from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: React.ElementType
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Tablero', icon: LayoutDashboard },
  { path: '/catalogo', label: 'Catálogo', icon: Package },
  { path: '/divisas', label: 'Divisas', icon: DollarSign },
  { path: '/tiendas', label: 'Tiendas', icon: Store },
  { path: '/comparativas', label: 'Comparativas', icon: Scale },
  { path: '/alertas', label: 'Alertas', icon: Bell },
  { path: '/about', label: 'Acerca de', icon: Info },
  { path: '/demo', label: 'Demo', icon: Monitor },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${isActive
      ? 'bg-indigo-600 text-white'
      : 'text-slate-600 hover:bg-slate-200 hover:text-slate-900'}`

  return (
    <aside
      id="primary-navigation"
      aria-label="Navegación principal"
      className={`fixed left-0 top-16 bottom-0 z-20 w-64 transform border-r border-slate-200 bg-white transition-transform duration-300 ease-in-out ${open ? 'translate-x-0' : '-translate-x-full'} md:static md:translate-x-0 md:shadow-none`}
    >
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-200">
        <span className="text-xl font-bold tracking-tight text-slate-900">PriceScope</span>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1.5 text-slate-500 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 md:hidden"
          aria-label="Cerrar menú de navegación"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={onClose}
              className={({ isActive }: { isActive: boolean }) => navLinkClass({ isActive })}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-slate-200">
        <p className="text-center text-[10px] leading-none text-slate-500">
          NoCountry S10-26, Equipo 14
        </p>
      </div>
    </aside>
  )
}
