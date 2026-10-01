import {
  AlertTriangle,
  Blend,
  CheckCircle2,
  CircleDot,
  Cog,
  Droplet,
  Droplets,
  Flame,
  FlaskConical,
  Hand,
  type LucideIcon,
  Power,
  Ruler,
  Scissors,
  Search,
  Shield,
  Sparkles,
  Zap,
} from 'lucide-react'
import type { Step } from './types'

const ICON_MAP: Record<string, LucideIcon> = {
  wear_gloves: Hand,
  gloves: Hand,
  cut: Scissors,
  sharp: Scissors,
  heat: Flame,
  hot: Flame,
  check: CheckCircle2,
  inspect: Search,
  power_off: Power,
  power_on: Power,
  power: Power,
  electrical: Zap,
  electricity: Zap,
  chemical: FlaskConical,
  chemicals: FlaskConical,
  moving_parts: Cog,
  machine: Cog,
  wash_hands: Droplets,
  water: Droplets,
  clean: Sparkles,
  measure: Ruler,
  mix: Blend,
  pour: Droplet,
  wear_mask: Shield,
  ppe: Shield,
  warning: AlertTriangle,
  careful: AlertTriangle,
}

export function iconFor(step: Pick<Step, 'icon' | 'is_safety_warning'>): LucideIcon {
  const key = (step.icon || '').trim().toLowerCase()
  if (ICON_MAP[key]) return ICON_MAP[key]
  return step.is_safety_warning ? AlertTriangle : CircleDot
}
