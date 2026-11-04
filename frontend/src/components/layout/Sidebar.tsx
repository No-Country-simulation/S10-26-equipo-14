import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard,
  Package,
  Scale,
  DollarSign,
  Bell,
  Info,
  Monitor,
  X,
  ChevronLeft,
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
  { path: '/comparativas', label: 'Comparativas', icon: Scale },
  { path: '/alertas', label: 'Alertas', icon: Bell },
  { path: '/about', label: 'Acerca de', icon: Info },
  { path: '/demo', label: 'Demo', icon: Monitor },
]

interface SidebarProps {
  open: boolean
}

export default function Sidebar({ open }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors rounded-lg ${isActive
      ? 'bg-indigo-600 text-white'
      : 'text-slate-600 hover:bg-slate-200 hover:text-slate-900'}${collapsed ? ' justify-center px-2' : ''}`

  return (
    <aside
      className={`fixed left-0 top-16 bottom-0 z-20 w-64 bg-white border-r border-slate-200 transform transition-transform duration-300 ease-in-out ${open ? 'translate-x-0' : '-translate-x-full'} md:static md:translate-x-0 md:w-64 md:shadow-none ${collapsed ? 'md:w-20' : ''}`}
    >
      <div className="flex h-16 items-center justify-between px-4 border-b border-slate-200">
        {!collapsed && (
          <>
            <span className="text-xl font-bold text-slate-900 tracking-tight">PriceScope</span>
            <button
              onClick={() => setCollapsed(true)}
              className="p-1.5 text-slate-500 hover:text-slate-900 md:hidden"
              aria-label="Colapsar menú"
            >
              <X className="h-5 w-5" />
            </button>
          </>
        )}
        {collapsed && (
          <button
            onClick={() => setCollapsed(false)}
            className="p-1.5 text-slate-500 hover:text-slate-900"
            aria-label="Expandir menú"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }: { isActive: boolean }) => navLinkClass({ isActive })}
            >
              <Icon className={`h-5 w-5 ${collapsed ? 'mx-auto' : ''}`} />
              {!collapsed && item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-4 border-t border-slate-200">
        <p className={collapsed ? 'hidden' : 'text-[10px] text-slate-500 text-center leading-none'}>
          NoCountry S10-26, Equipo 14
        </p>
      </div>
    </aside>
  )
}