import clsx from 'clsx'
import { ArrowLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="group mb-7 inline-flex items-center gap-2 rounded-full border border-border bg-white px-3.5 py-1.5 text-sm font-medium text-ink-soft shadow-xs transition-all hover:border-border-strong hover:text-ink"
    >
      <ArrowLeft size={15} className="transition-transform group-hover:-translate-x-0.5" />
      {children}
    </Link>
  )
}

export function PageHeader({
  title,
  subtitle,
  right,
  devanagari,
}: {
  title: ReactNode
  subtitle?: ReactNode
  right?: ReactNode
  devanagari?: boolean
}) {
  return (
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className={clsx('text-3xl font-extrabold tracking-tight text-ink', devanagari && 'lang-dev text-4xl')}>
          {title}
        </h1>
        {subtitle && (
          <p className={clsx('mt-2 max-w-xl text-ink-soft', devanagari && 'lang-dev text-lg')}>{subtitle}</p>
        )}
      </div>
      {right}
    </header>
  )
}

export function Shell({ wide, children }: { wide?: boolean; children: ReactNode }) {
  return (
    <div
      className={clsx(
        'mx-auto w-full px-5 pb-20 pt-10 sm:px-8',
        wide ? 'max-w-5xl' : 'max-w-3xl',
      )}
    >
      {children}
    </div>
  )
}
