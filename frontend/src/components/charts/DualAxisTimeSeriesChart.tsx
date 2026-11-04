import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import type { TooltipProps } from 'recharts'

interface SeriesPoint {
  date: string
  price: number | null
  rate: number | null
}

interface DualAxisTimeSeriesChartProps {
  data: SeriesPoint[]
  title?: string
  subtitle?: string
  className?: string
}

function formatTooltipValue(value: number | null, prefix: string, decimals: number) {
  if (value === null) return '—'
  return `${prefix} ${value.toFixed(decimals)}`
}

function formatDateLabel(value: string) {
  const d = new Date(value)
  return d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
}

export default function DualAxisTimeSeriesChart({
  data,
  title,
  subtitle,
  className,
}: DualAxisTimeSeriesChartProps) {
  const hasPriceData = data.some((d) => d.price !== null)
  const hasRateData = data.some((d) => d.rate !== null)

  const customTooltip = ({ active, payload }: TooltipProps<any, any>) => {
    if (active !== true || !payload || !payload.length) {
      return null
    }
    const date = payload[0].payload?.date as string | undefined
      const pricePayload = (payload as unknown as { payload?: SeriesPoint }[]).find(
        (p) => p.payload?.price !== null
      )
      const ratePayload = (payload as unknown as { payload?: SeriesPoint }[]).find(
        (p) => p.payload?.rate !== null
      )

      const price = (pricePayload?.payload?.price ?? null) as number | null
      const rate = (ratePayload?.payload?.rate ?? null) as number | null

      return (
        <div className="p-3 border border-slate-200 rounded-lg bg-white text-sm text-slate-900 shadow-md">
          <div className="font-medium text-slate-700">{date ? formatDateLabel(date) : '—'}</div>
          {hasPriceData && (
            <div className="text-blue-600">{formatTooltipValue(price, 'Precio:', 2)} ARS</div>
          )}
          {hasRateData && (
            <div className="text-indigo-600">{formatTooltipValue(rate, 'Tipo de cambio:', 2)} ARS/USD</div>
          )}
        </div>
      )
    }

  return (
    <div className={className}>
      {title && (
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
      )}
      <div className="h-64 w-full border border-slate-200 bg-slate-50 relative pl-8 pr-8">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: 20, right: 70 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateLabel}
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={{ stroke: '#cbd5e1' }}
            />
            {hasPriceData && (
              <YAxis
                orientation="left"
                label={{ value: 'Precio (ARS)', angle: -90, position: 'left', offset: 0 }}
                tick={{ fontSize: 12, fill: '#64748b' }}
                axisLine={{ stroke: '#cbd5e1' }}
                domain={['dataMin', 'dataMax']}
                tickFormatter={(v) => `$${v}`}
              />
            )}
            {hasRateData && (
              <YAxis
                orientation="right"
                label={{ value: 'Tipo de cambio (ARS/USD)', angle: -90, position: 'right', offset: 0 }}
                tick={{ fontSize: 12, fill: '#64748b' }}
                axisLine={{ stroke: '#cbd5e1' }}
                domain={['dataMin', 'dataMax']}
                tickFormatter={(v) => `$${v}`}
              />
            )}
            <Tooltip content={customTooltip} />
            <Legend />
            {hasPriceData && (
              <Line
                type="monotone"
                dataKey="price"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                name="Precio"
              />
            )}
            {hasRateData && (
              <Line
                type="monotone"
                dataKey="rate"
                stroke="#4f46e5"
                strokeWidth={2}
                dot={false}
                name="Tipo de cambio"
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}