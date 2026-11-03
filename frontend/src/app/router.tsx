import { createBrowserRouter } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import AboutPage from '../pages/AboutPage'
import HomePage from '../pages/HomePage'
import DemoPage from '../pages/DemoPage'
import CatalogoPage from '../pages/CatalogoPage'

const ComingSoon = () => (
  <section className="mx-auto max-w-2xl py-12 text-center">
    <h1 className="text-2xl font-bold text-slate-900">Página en construcción</h1>
    <p className="mt-4 text-slate-600">
      Esta sección forma parte de las próximas épicas del roadmap (Semana 2 en adelante).
    </p>
  </section>
)

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'demo', element: <DemoPage /> },
      { path: 'catalogo', element: <CatalogoPage /> },
      { path: 'comparativas', element: <ComingSoon /> },
      { path: 'divisas', element: <ComingSoon /> },
      { path: 'alertas', element: <ComingSoon /> },
    ],
  },
])
