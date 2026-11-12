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
          <h1 className="text-2xl font-bold text-slate-900">Demo visual de componentes</h1>
          <p className="mt-1 text-sm text-slate-500">
            Muestra de componentes de interfaz. Las métricas y series son sintéticas.
          </p>
        </div>
      </div>

      <div role="note" className="rounded-xl border-2 border-amber-400 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">Datos sintéticos de demostración</p>
        <p className="mt-1">Las métricas y series son valores fijos de ejemplo; no proceden de la API ni representan precios actuales.</p>
      </div>

      <div className="space-y-8 rounded-2xl border-2 border-dashed border-amber-300 bg-amber-50/30 p-3 sm:p-5">
      <p className="text-center text-xs font-semibold uppercase tracking-wide text-amber-900">Muestra sintética · no representa datos actuales</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Inflación acumulada · ejemplo</CardTitle>
            <CardDescription className="text-xs">Últimos 30 días · dato sintético</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="blue">12,4%</Metric>
            <DemoBadge>+0,8 pp</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Dólar oficial · ejemplo</CardTitle>
            <CardDescription className="text-xs">Cotización sintética</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="indigo">$ 980,50</Metric>
            <DemoBadge>+1,2%</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Dólar blue · ejemplo</CardTitle>
            <CardDescription className="text-xs">Cotización sintética</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="blue">$ 1.240,00</Metric>
            <DemoBadge>-0,4%</DemoBadge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Brecha cambiaria · ejemplo</CardTitle>
            <CardDescription className="text-xs">Oficial frente al blue · dato sintético</CardDescription>
          </CardHeader>
          <CardContent>
            <Metric color="red">26,5%</Metric>
            <DemoBadge>+0,3 pp</DemoBadge>
          </CardContent>
        </Card>
      </div>

      <section className="rounded-xl border border-amber-300 bg-white p-4 sm:p-5" aria-label="Escenario analítico simulado">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <DemoBadge color="red">DEMO / DATOS SIMULADOS</DemoBadge>
          <span className="text-xs text-slate-500">Ejemplo pedagógico separado de las observaciones reales</span>
        </div>
        <h2 className="font-semibold text-slate-900">Posible reduflación · bebida</h2>
        <p className="mt-2 text-sm text-slate-700">Presentación anterior: 1 L por $ 1.000 ($ 1.000/L). Presentación nueva: 900 ml por $ 950 ($ 1.055,56/L).</p>
        <p className="mt-1 text-sm text-slate-700">Contenido −10%; precio total −5%; precio unitario +5,56%. El contenido baja y el precio no cae en la misma proporción: señal <strong>possible</strong>.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-amber-50 p-3"><p className="text-xs text-slate-500">Inflación simulada del período</p><p className="font-semibold">12,4%</p></div>
          <div className="rounded-lg bg-amber-50 p-3"><p className="text-xs text-slate-500">Variación cambiaria simulada</p><p className="font-semibold">11,6%</p></div>
          <div className="rounded-lg bg-amber-50 p-3"><p className="text-xs text-slate-500">Diferencia simulada</p><p className="font-semibold">+0,8 puntos porcentuales</p></div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Índice de precios · serie de ejemplo</CardTitle>
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
            <CardTitle className="text-sm">Precio por tienda · ejemplo</CardTitle>
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
          <CardTitle className="text-sm">Evolución del área de cobertura · ejemplo</CardTitle>
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
      </div>
    </section>
  )
}
