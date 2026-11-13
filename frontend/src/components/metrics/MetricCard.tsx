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
        "group rounded-2xl border border-slate-200/80 border-t-[3px] border-t-cyan-500 bg-white p-5 shadow-[0_5px_20px_-14px_rgba(8,47,73,0.35)] transition-all hover:-translate-y-0.5 hover:shadow-md sm:p-6",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            {title}
          </p>
          <p className="mt-2 text-3xl font-bold tracking-tight tabular-nums text-[#0b2e50]">
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
