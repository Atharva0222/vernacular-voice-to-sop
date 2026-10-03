// Chart ink, kept separate from the app's UI-chrome palette (primary/safe/caution/stop in
// index.css) on purpose: those tokens don't validate as a categorical set (indigo-vs-blue and
// amber-vs-green both fail the colorblind-safety check - see the dataviz skill's palette
// validator), so chart series use the skill's own pre-validated sequential ramp instead.
// Chart chrome (grid/axis/label ink) reuses the app's existing neutral tokens for consistency.

// Sequential blue, light -> dark (dataviz skill reference palette). Used for every "compare
// magnitude across categories" chart on the dashboard - per the skill, that job calls for one
// hue, not a rainbow of categorical colors.
export const SEQUENTIAL_BLUE = {
  100: '#cde2fb',
  200: '#9ec5f4',
  300: '#6da7ec',
  400: '#3987e5',
  500: '#256abf',
  600: '#184f95',
  700: '#0d366b',
} as const

export const CHART_BAR_COLOR = SEQUENTIAL_BLUE[400]
export const CHART_BAR_COLOR_MUTED = SEQUENTIAL_BLUE[200]

// Status accents reuse the app's own existing tokens (index.css) - these are the plant-floor
// ISO-style red/amber/green, kept for STATUS use (always paired with a text label, never
// color-alone) rather than as chart-series identity, where that trio fails CVD validation.
export const STATUS_GOOD = '#16a34a'
export const STATUS_WARNING = '#d97706'
export const STATUS_CRITICAL = '#dc2626'

// Chart chrome - one step off the app's own surface, matching its existing neutral ramp.
export const CHART_GRID = '#e9ebf3' // --color-border
export const CHART_AXIS_TEXT = '#64748b' // --color-ink-soft
export const CHART_MUTED_TEXT = '#94a3b8' // --color-ink-faint
