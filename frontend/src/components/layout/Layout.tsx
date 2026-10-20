import { NavLink, Outlet } from 'react-router-dom'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? 'bg-indigo-600 text-white'
      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-base font-bold text-white">
              P
            </span>
            <div>
              <p className="text-lg font-semibold leading-none">PriceScope</p>
              <p className="mt-1 text-xs text-slate-500">
                Monitor de Inflación Real Multimoneda
              </p>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navLinkClass}>
              Inicio
            </NavLink>
            <NavLink to="/about" className={navLinkClass}>
              Acerca de
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4 text-center text-sm text-slate-500">
          PriceScope — NoCountry S10-26, Equipo 14
        </div>
      </footer>
    </div>
  )
}
