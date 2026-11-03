import {
  LineChart as RLineChart,
  BarChart as RBarChart,
  AreaChart as RAreaChart,
  ResponsiveContainer,
  Legend as RLegend,
  Tooltip,
  CartesianGrid,
  XAxis,
  YAxis,
  Line,
  Bar,
  Area,
} from 'recharts'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge as ShadcnBadge } from '@/components/ui/badge'

const metricColors = {
  blue: 'text-blue-600',
  indigo: 'text-indigo-600',
  red: 'text-red-600',
} as const

const badgeColors = {
  blue: 'border-blue-200 bg-blue-50 text-blue-700',
  red: 'border-red-200 bg-red-50 text-red-700',
  green: 'border-green-200 bg-green-50 text-green-700',
  gray: 'border-slate-200 bg-slate-100 text-slate-700',
} as const

function Metric({ color, children }: { color: keyof typeof metricColors; children: ReactNode }) {
  return <p className={`text-3xl font-semibold tracking-tight ${metricColors[color]}`}>{children}</p>
}

function DemoBadge({ color = 'gray', children }: { color?: keyof typeof badgeColors; children: ReactNode }) {
  return (
    <ShadcnBadge variant="outline" className={`h-5 px-2 py-0.5 text-xs ${badgeColors[color]}`}>
      {children}
    </ShadcnBadge>
  )
}

const lineData = [
  { month: 'Ene', precio: 100, tipoCambio: 950 },
  { month: 'Feb', precio: 105, tipoCambio: 980 },
  { month: 'Mar', precio: 102, tipoCambio: 1020 },
  { month: 'Abr', precio: 110, tipoCambio: 1080 },
  { month: 'May', precio: 108, tipoCambio: 1150 },
  { month: 'Jun', precio: 115, tipoCambio: 1200 },
]

const barData = [
  { store: 'Tienda A', price: 1200 },
  { store: 'Tienda B', price: 1150 },
  { store: 'Tienda C', price: 1300 },
  { store: 'Tienda D', price: 1180 },
  { store: 'Tienda E', price: 1220 },
]

const areaData = [
  { month: 'Ene', value: 40 },
  { month: 'Feb', value: 65 },
  { month: 'Mar', value: 50 },
  { month: 'Abr', value: 80 },
  { month: 'May', value: 70 },
  { month: 'Jun', value: 95 },
]

export default function DemoPage() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Demo - Librerias instaladas</h1>
          <p className="mt-1 text-sm text-slate-500">
            Muestra de componentes locales y shadcn/ui con Tailwind CSS v4.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Inflacion acumulada</CardTitle>
            <CardDescription className="text-xs">Ultimos 30 dias</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="blue">12,4%</Metric>
            <DemoBadge>+0,8 pp</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Dolar oficial</CardTitle>
            <CardDescription className="text-xs">Cotizacion vigente</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="indigo">$ 980,50</Metric>
            <DemoBadge>+1,2%</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Dolar blue</CardTitle>
            <CardDescription className="text-xs">Cotizacion paralela</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="blue">$ 1.240,00</Metric>
            <DemoBadge>-0,4%</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Brecha cambiaria</CardTitle>
            <CardDescription className="text-xs">Oficial vs. Blue</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="red">26,5%</Metric>
            <DemoBadge>+0,3 pp</DemoBadge>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Indice de precios - serie temporal</CardTitle>
          </CardHeader>
          <CardContent className="h-64 w-full border border-slate-200 bg-slate-50 relative">
            <ResponsiveContainer width="100%" height="100%">
              <RLineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <RLegend />
                <Line type="monotone" dataKey="precio" stroke="#3b82f6" />
                <Line type="monotone" dataKey="tipoCambio" stroke="#4f46e5" />
              </RLineChart>
            </ResponsiveContainer>
            <RLegend />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Precio por tienda</CardTitle>
          </CardHeader>
          <CardContent className="h-64 w-full border border-slate-200 bg-slate-50 relative">
            <ResponsiveContainer width="100%" height="100%">
              <RBarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="store" />
                <YAxis />
                <Tooltip />
                <RLegend />
                <Bar dataKey="price" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </RBarChart>
            </ResponsiveContainer>
            <RLegend />
          </CardContent>
        </Card>
      </div>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-sm">Evolucion del area de cobertura</CardTitle>
        </CardHeader>
        <CardContent className="h-64 w-full border border-slate-200 bg-slate-50 relative">
          <ResponsiveContainer width="100%" height="100%">
            <RAreaChart data={areaData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="value" fill="#3b82f6" opacity={0.6} />
            </RAreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <div className="flex items-center gap-2">
          <DemoBadge color="blue">Activo</DemoBadge>
          <ShadcnBadge variant="default"> shadcn/ui </ShadcnBadge>
        </div>
        <div className="flex items-center gap-2">
          <DemoBadge color="red">Alerta</DemoBadge>
          <ShadcnBadge variant="destructive"> shadcn/ui </ShadcnBadge>
        </div>
        <div className="flex items-center gap-2">
          <DemoBadge color="green">Positivo</DemoBadge>
          <ShadcnBadge variant="secondary"> shadcn/ui </ShadcnBadge>
        </div>
        <div className="flex items-center gap-2">
          <DemoBadge>Sin datos</DemoBadge>
          <ShadcnBadge variant="outline"> shadcn/ui </ShadcnBadge>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Button>Base UI Button</Button>
        <Button variant="outline">shadcn/ui Button</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    </section>
  )
}
