import { useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

const ROUTE_LABELS: Record<string, string> = {
  '/': 'Tablero',
  '/catalogo': 'Catálogo',
  '/divisas': 'Divisas',
  '/comparativas': 'Comparativas',
  '/alertas': 'Alertas',
  '/about': 'Acerca de',
  '/demo': 'Demo',
}

export default function Breadcrumbs() {
  const location = useLocation()
  const path = location.pathname

  const segments = path.split('/').filter(Boolean)
  const crumbs = segments.map((_, index) => {
    const route = '/' + segments.slice(0, index + 1).join('/')
    return {
      label: ROUTE_LABELS[route] || route,
      path: route,
      isLast: index === segments.length - 1,
    }
  })

  return (
    <nav className="flex items-center gap-1 text-[11px] text-slate-500" aria-label="Breadcrumbs">
      {crumbs.map((crumb, index) => (
        <span key={crumb.path} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="h-3 w-3" />}
          {crumb.isLast ? (
            <span className="text-slate-900 font-medium">{crumb.label}</span>
          ) : (
            <a href={crumb.path} className="hover:text-indigo-600 underline underline-offset-4">
              {crumb.label}
            </a>
          )}
        </span>
      ))}
    </nav>
  )
}