import clsx from 'clsx'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { Loader2, type LucideIcon } from 'lucide-react'
import {
  type ButtonHTMLAttributes,
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
type Size = 'sm' | 'md' | 'lg'

const buttonVariants: Record<Variant, string> = {
  primary:
    'bg-gradient-to-br from-primary to-primary-to text-white shadow-md shadow-primary/25 hover:shadow-glow hover:-translate-y-0.5',
  secondary: 'bg-white text-ink border border-border-strong hover:border-ink-soft hover:-translate-y-0.5',
  ghost: 'bg-transparent text-ink-soft hover:bg-black/5',
  danger:
    'bg-gradient-to-br from-rose-500 to-red-600 text-white shadow-md shadow-red-500/25 hover:shadow-lg hover:-translate-y-0.5',
  success:
    'bg-gradient-to-br from-emerald-500 to-green-600 text-white shadow-md shadow-emerald-500/25 hover:shadow-lg hover:-translate-y-0.5',
}

const buttonSizes: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-sm rounded-lg gap-1.5',
  md: 'px-5 py-2.5 text-sm rounded-xl gap-2',
  lg: 'px-7 py-3.5 text-base rounded-2xl gap-2.5',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = 'primary', size = 'md', loading, disabled, children, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center font-semibold transition-all duration-200 active:scale-[0.97] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none',
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    >
      {loading && <Loader2 size={16} className="animate-spin" />}
      {children}
    </button>
  )
})

type BadgeVariant = 'neutral' | 'primary' | 'info' | 'safe' | 'caution' | 'stop' | 'violet' | 'dark'

const badgeStyles: Record<BadgeVariant, string> = {
  neutral: 'bg-slate-100 text-ink-soft',
  primary: 'bg-primary-light text-primary-dark',
  info: 'bg-info-bg text-info',
  safe: 'bg-safe-bg text-safe',
  caution: 'bg-caution-bg text-caution',
  stop: 'bg-stop-bg text-stop',
  violet: 'bg-violet-bg text-violet',
  dark: 'bg-ink text-white',
}

export function Badge({
  variant = 'neutral',
  children,
  className,
  icon: Icon,
}: {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
  icon?: LucideIcon
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold tabular-nums',
        badgeStyles[variant],
        className,
      )}
    >
      {Icon && <Icon size={12} />}
      {children}
    </span>
  )
}

export function Card({ className, children, ...props }: HTMLMotionProps<'div'>) {
  return (
    <motion.div className={clsx('rounded-3xl border border-border bg-surface p-6 shadow-sm', className)} {...props}>
      {children}
    </motion.div>
  )
}

export const Field = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Field(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={clsx(
        'w-full rounded-xl border border-border-strong bg-white px-4 py-2.5 text-sm text-ink outline-none transition-all placeholder:text-ink-faint focus:border-primary focus:ring-4 focus:ring-primary/10',
        className,
      )}
      {...props}
    />
  )
})

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <select
      ref={ref}
      className={clsx(
        'rounded-xl border border-border-strong bg-white px-4 py-2.5 text-sm text-ink outline-none transition-all focus:border-primary focus:ring-4 focus:ring-primary/10',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  )
})

export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return <Loader2 size={size} className={clsx('animate-spin', className)} />
}

export function EmptyState({
  icon: Icon,
  title,
  subtitle,
  action,
  className,
}: {
  icon?: LucideIcon
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center gap-2 rounded-3xl border border-dashed border-border-strong bg-white/60 px-8 py-16 text-center',
        className,
      )}
    >
      {Icon && (
        <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-light text-primary">
          <Icon size={26} />
        </div>
      )}
      <p className="text-lg font-semibold text-ink">{title}</p>
      {subtitle && <p className="max-w-sm text-sm text-ink-soft">{subtitle}</p>}
      {action}
    </div>
  )
}

export function Alert({ children }: { children: ReactNode }) {
  return (
    <div className="mb-5 flex items-start gap-3 rounded-2xl border border-stop/20 bg-stop-bg px-4 py-3 text-sm font-medium text-stop">
      {children}
    </div>
  )
}
