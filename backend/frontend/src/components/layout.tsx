import clsx from 'clsx'
import { ArrowLeft, LogOut } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { signOut } from '../lib/session'

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

export function WhoAmI({ name, role }: { name: string; role: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-full border border-border bg-white py-1.5 pl-1.5 pr-3 shadow-xs">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-to text-xs font-bold text-white">
        {name.charAt(0).toUpperCase()}
      </div>
      <span className="text-sm font-semibold text-ink">{name}</span>
      <span className="hidden text-xs text-ink-faint sm:inline">· {role.replace('_', ' ')}</span>
      <button
        onClick={signOut}
        className="ml-1 rounded-full p-1 text-ink-faint transition-colors hover:bg-stop-bg hover:text-stop"
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut size={14} />
      </button>
    </div>
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
