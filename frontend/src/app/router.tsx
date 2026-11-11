import { createBrowserRouter } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import {
  AboutRoute,
  CatalogoRoute,
  ComingSoon,
  DemoRoute,
  DivisasRoute,
  HomeRoute,
  NotFoundRoute,
  TiendasRoute,
} from './route-pages'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomeRoute /> },
      { path: 'about', element: <AboutRoute /> },
      { path: 'demo', element: <DemoRoute /> },
      { path: 'catalogo', element: <CatalogoRoute /> },
      { path: 'divisas', element: <DivisasRoute /> },
      { path: 'tiendas', element: <TiendasRoute /> },
      { path: 'comparativas', element: <ComingSoon /> },
      { path: 'alertas', element: <ComingSoon /> },
      { path: '*', element: <NotFoundRoute /> },
    ],
  },
])
