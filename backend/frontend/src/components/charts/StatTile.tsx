import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

type Accent = 'neutral' | 'critical' | 'good'

const accentStyles: Record<Accent, string> = {
  neutral: 'bg-primary-light text-primary-dark',
  critical: 'bg-stop-bg text-stop',
  good: 'bg-safe-bg text-safe',
}

/** KPI stat tile: a label, a large proportional-figure value (never tabular-nums - that's only
 * for columns that must align), and an optional icon carrying the accent. One glance, no chart
 * needed - per the dataviz skill, a single current value is a stat tile, not a one-bar chart. */
export function StatTile({
  label,
  value,
  icon: Icon,
  accent = 'neutral',
}: {
  label: string
  value: string | number
  icon?: LucideIcon
  accent?: Accent
}) {
  return (
    <div className="rounded-2xl border border-border bg-white p-5 shadow-xs">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink-soft">{label}</span>
        {Icon && (
          <span className={clsx('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', accentStyles[accent])}>
            <Icon size={18} />
          </span>
        )}
      </div>
      <div className="mt-2 text-3xl font-bold text-ink">{value}</div>
    </div>
  )
}
