import { lazy, Suspense } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Skeleton } from '../components/ui/skeleton'

function PageLoading() {
  return (
    <section aria-label="Cargando página" className="mx-auto max-w-7xl space-y-4 px-4 py-8">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-40 w-full" />
    </section>
  )
}

const AboutPage = lazy(() => import('../pages/AboutPage'))
const HomePage = lazy(() => import('../pages/HomePage'))
const DemoPage = lazy(() => import('../pages/DemoPage'))
const CatalogoPage = lazy(() => import('../pages/CatalogoPage'))
const DivisasPage = lazy(() => import('../pages/DivisasPage'))
const TiendasPage = lazy(() => import('../pages/TiendasPage'))

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<PageLoading />}>{element}</Suspense>
}

export function HomeRoute() { return withSuspense(<HomePage />) }
export function AboutRoute() { return withSuspense(<AboutPage />) }
export function DemoRoute() { return withSuspense(<DemoPage />) }
export function CatalogoRoute() {
  const location = useLocation()
  return withSuspense(<CatalogoPage key={location.search} />)
}
export function DivisasRoute() { return withSuspense(<DivisasPage />) }
export function TiendasRoute() { return withSuspense(<TiendasPage />) }

export function ComingSoon() {
  return (
    <section className="mx-auto max-w-2xl py-12 text-center">
      <h1 className="text-2xl font-bold text-slate-900">Página en construcción</h1>
      <p className="mt-4 text-slate-600">
        Esta sección forma parte de las próximas épicas del roadmap (Semana 2 en adelante).
      </p>
    </section>
  )
}

export function NotFoundRoute() {
  return (
    <section className="mx-auto max-w-2xl py-16 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-indigo-700">Error 404</p>
      <h1 className="mt-2 text-3xl font-bold text-slate-900">No encontramos esta página</h1>
      <p className="mt-3 text-slate-600">La dirección puede haber cambiado o no existir.</p>
      <Link to="/" className="mt-6 inline-flex rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700">
        Volver al inicio
      </Link>
    </section>
  )
}
