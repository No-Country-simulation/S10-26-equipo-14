import { createBrowserRouter } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import AboutPage from '../pages/AboutPage'
import HomePage from '../pages/HomePage'
import DemoPage from '../pages/DemoPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'demo', element: <DemoPage /> },
    ],
  },
])
