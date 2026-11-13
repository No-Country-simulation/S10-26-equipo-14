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

interface SeriesPoint {
  date: string
  price: number | null
  rate: number | null
  parallelRate?: number | null
}

interface DualAxisTimeSeriesChartProps {
  data: SeriesPoint[]
  title?: string
  subtitle?: string
  className?: string
}

interface TooltipPoint {
  payload?: SeriesPoint
}

interface ChartTooltipProps {
  active?: boolean
  payload?: TooltipPoint[]
  hasPriceData: boolean
  hasRateData: boolean
  hasParallelRateData: boolean
}

const numberFormat = new Intl.NumberFormat('es-AR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function formatAmount(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) ? '—' : numberFormat.format(value)
}

function formatAxisAmount(value: number) {
  return new Intl.NumberFormat('es-AR', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function formatDateLabel(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('es-AR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function ChartTooltip({ active, payload, hasPriceData, hasRateData, hasParallelRateData }: ChartTooltipProps) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-900 shadow-md">
      <div className="mb-1 font-medium text-slate-700">Fecha y hora: {formatDateLabel(point.date)}</div>
      {hasPriceData && point.price !== null && (
        <div className="text-blue-700">Precio observado: ARS {formatAmount(point.price)}</div>
      )}
      {hasRateData && point.rate !== null && (
        <div className="text-violet-700">Cotización USD/ARS: {formatAmount(point.rate)} ARS por USD</div>
      )}
      {hasParallelRateData && point.parallelRate != null && (
        <div className="text-rose-700">Cotizacion paralela USD/ARS: {formatAmount(point.parallelRate)} ARS por USD</div>
      )}
    </div>
  )
}

export default function DualAxisTimeSeriesChart({
  data,
  title,
  subtitle,
  className,
}: DualAxisTimeSeriesChartProps) {
  const hasPriceData = data.some((point) => point.price !== null)
  const hasRateData = data.some((point) => point.rate !== null)
  const hasParallelRateData = data.some((point) => point.parallelRate != null)

  return (
    <div className={className}>
      {title && (
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
      )}
      <div className="relative h-72 w-full border border-slate-200 bg-slate-50 px-2 sm:px-3">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 14, left: 4, right: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateLabel}
              tick={{ fontSize: 12, fill: '#64748b' }}
              axisLine={{ stroke: '#cbd5e1' }}
              minTickGap={18}
            />
            {hasPriceData && (
              <YAxis
                yAxisId="price"
                orientation="left"
                width={62}
                domain={['auto', 'auto']}
                label={{ value: 'Precio promedio (ARS)', angle: -90, position: 'insideLeft', offset: 5, fontSize: 11 }}
                tick={{ fontSize: 11, fill: '#1d4ed8' }}
                axisLine={{ stroke: '#93c5fd' }}
                tickFormatter={formatAxisAmount}
              />
            )}
            {(hasRateData || hasParallelRateData) && (
              <YAxis
                yAxisId="rate"
                orientation="right"
                width={68}
                domain={['auto', 'auto']}
                label={{ value: 'Cotización (ARS por USD)', angle: 90, position: 'insideRight', offset: 5, fontSize: 11 }}
                tick={{ fontSize: 11, fill: '#6d28d9' }}
                axisLine={{ stroke: '#c4b5fd' }}
                tickFormatter={formatAxisAmount}
              />
            )}
            <Tooltip
              content={(props) => (
                <ChartTooltip
                  active={props.active}
                  payload={props.payload as TooltipPoint[] | undefined}
                  hasPriceData={hasPriceData}
                  hasRateData={hasRateData}
                  hasParallelRateData={hasParallelRateData}
                />
              )}
            />
            <Legend />
            {hasPriceData && (
              <Line
                yAxisId="price"
                type="linear"
                dataKey="price"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#2563eb' }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                name="Precio promedio (ARS)"
                isAnimationActive={false}
              />
            )}
            {hasRateData && (
              <Line
                yAxisId="rate"
                type="linear"
                dataKey="rate"
                stroke="#7c3aed"
                strokeWidth={2.5}
                strokeDasharray="6 3"
                dot={{ r: 3, fill: '#7c3aed' }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                name="Cotización USD/ARS (ARS por USD)"
                isAnimationActive={false}
              />
            )}
            {hasParallelRateData && (
              <Line
                yAxisId="rate"
                type="linear"
                dataKey="parallelRate"
                stroke="#e11d48"
                strokeWidth={2.5}
                strokeDasharray="3 3"
                dot={{ r: 3, fill: '#e11d48' }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                name="Cotizacion paralela USD/ARS (ARS por USD)"
                isAnimationActive={false}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
