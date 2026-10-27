import { createBrowserRouter } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import AboutPage from '../pages/AboutPage'
import HomePage from '../pages/HomePage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', element: <AboutPage /> },
    ],
  },
])
