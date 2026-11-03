import { cn } from "@/lib/utils"

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: {
    label: string
    value: string | number
    positive: boolean
  }
  className?: string
}

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white p-6 shadow-sm",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            {title}
          </p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {value}
          </p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {trend && (
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium",
              trend.positive
                ? "border-green-200 bg-green-50 text-green-700"
                : "border-red-200 bg-red-50 text-red-700",
            )}
          >
            {trend.label}: {trend.value}
          </span>
        )}
      </div>
    </div>
  )
}