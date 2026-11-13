import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import Breadcrumbs from './Breadcrumbs'
import Footer from './Footer'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-[#f4f7fb] text-slate-900">
      <TopBar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} sidebarOpen={sidebarOpen} />

      <div className="flex flex-1 overflow-hidden relative">
        {sidebarOpen && (
          <button
            type="button"
            aria-label="Cerrar menú de navegación"
            className="fixed inset-0 z-10 cursor-default bg-black/40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <main className="flex-1 w-full overflow-y-auto bg-[#f4f7fb]">
          <div className="mx-auto max-w-6xl px-4 py-8">
            <Breadcrumbs />
            <Outlet />
          </div>
        </main>
      </div>

      <Footer />
    </div>
  )
}
