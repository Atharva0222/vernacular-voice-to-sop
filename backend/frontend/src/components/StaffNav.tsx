import clsx from 'clsx'
import { NavLink } from 'react-router-dom'
import type { Role } from '../lib/types'

const LINKS: { to: string; label: string; roles?: Role[] }[] = [
  { to: '/machines', label: 'SOP' },
  { to: '/inbox', label: 'Inbox', roles: ['manager', 'plant_head'] },
  { to: '/employees', label: 'Employees' },
  { to: '/workforce', label: 'Workforce', roles: ['supervisor', 'manager', 'plant_head', 'hr_admin'] },
  { to: '/hr', label: 'HR' },
]

/** The persistent tab bar across staff-facing modules (voice-to-SOP today, Employees now,
 * Workforce/HR to follow) - workers never see this, since they never have a session at all. */
export function StaffNav({ role }: { role: Role }) {
  const visible = LINKS.filter((l) => !l.roles || l.roles.includes(role))
  return (
    <nav className="flex items-center gap-1 rounded-full border border-border bg-white p-1 shadow-xs">
      {visible.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            clsx(
              'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
              isActive ? 'bg-primary-light text-primary-dark' : 'text-ink-soft hover:bg-black/5',
            )
          }
        >
          {l.label}
        </NavLink>
      ))}
    </nav>
  )
}
