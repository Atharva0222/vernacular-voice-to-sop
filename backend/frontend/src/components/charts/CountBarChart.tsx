import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { CHART_AXIS_TEXT, CHART_BAR_COLOR, CHART_GRID } from '../../lib/chartColors'

export interface CountBarDatum {
  label: string
  value: number
  /** Overrides the default sequential fill for this one bar - used sparingly, for emphasis
   * (e.g. an escalated/critical row), never to turn this into a rainbow categorical chart. */
  color?: string
}

/** Horizontal "compare magnitude across categories" bar chart: one sequential hue, a thin bar
 * (capped, never filling its slot), a rounded data-end, and the value labeled directly at the
 * tip rather than relying on axis gridlines alone - per the dataviz skill's mark spec. A single
 * series needs no legend box, so this never renders one. */
export function CountBarChart({ data, height = 220 }: { data: CountBarDatum[]; height?: number }) {
  const maxValue = Math.max(1, ...data.map((d) => d.value))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 0 }} barCategoryGap="30%">
        <XAxis type="number" domain={[0, maxValue]} hide />
        <YAxis
          type="category"
          dataKey="label"
          width={120}
          tickLine={false}
          axisLine={{ stroke: CHART_GRID }}
          tick={{ fill: CHART_AXIS_TEXT, fontSize: 14 }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.color ?? CHART_BAR_COLOR} />
          ))}
          <LabelList dataKey="value" position="right" style={{ fill: '#0f172a', fontSize: 14, fontWeight: 600 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
