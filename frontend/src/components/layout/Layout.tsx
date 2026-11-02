import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import Breadcrumbs from './Breadcrumbs'
import Footer from './Footer'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <TopBar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

      <div className="flex flex-1 overflow-hidden relative">
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/40 z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <Sidebar open={sidebarOpen} />
        <main className="flex-1 w-full overflow-y-auto bg-slate-50">
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
