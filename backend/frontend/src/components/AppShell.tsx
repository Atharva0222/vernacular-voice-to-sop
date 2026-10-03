import clsx from 'clsx'
import {
  Briefcase,
  Clock,
  Cog,
  Inbox as InboxIcon,
  LayoutDashboard,
  LogOut,
  Sparkles,
  Users,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { signOut } from '../lib/session'
import type { Role } from '../lib/types'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  roles?: Role[]
}

const NAV: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/machines', label: 'SOP cards', icon: Cog },
  { to: '/inbox', label: 'Inbox', icon: InboxIcon, roles: ['manager', 'plant_head'] },
  { to: '/employees', label: 'Employees', icon: Users },
  { to: '/workforce', label: 'Workforce', icon: Clock, roles: ['supervisor', 'manager', 'plant_head', 'hr_admin'] },
  { to: '/hr', label: 'HR', icon: Briefcase },
]

const ROLE_LABEL: Record<Role, string> = {
  supervisor: 'Supervisor',
  manager: 'Manager',
  plant_head: 'Plant Head',
  hr_admin: 'HR Admin',
  recruiter: 'Recruiter',
}

/** The persistent staff shell: a left sidebar (nav + identity) and a wide content column. Every
 * signed-in staff page renders its content inside this instead of hand-rolling a top pill-nav +
 * WhoAmI badge per page - workers never see this at all, since they never have a session. */
export function AppShell({ role, name, children }: { role: Role; name: string; children: ReactNode }) {
  const visible = NAV.filter((item) => !item.roles || item.roles.includes(role))

  return (
    <div className="flex min-h-screen bg-canvas">
      <aside className="flex w-72 shrink-0 flex-col border-r border-border bg-white">
        <div className="flex items-center gap-2.5 px-6 py-7">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-to text-white shadow-sm">
            <Sparkles size={18} />
          </span>
          <span className="text-lg font-extrabold tracking-tight text-ink">Bolo</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-4">
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-base font-semibold transition-colors',
                  isActive ? 'bg-primary-light text-primary-dark' : 'text-ink-soft hover:bg-canvas hover:text-ink',
                )
              }
            >
              <item.icon size={19} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border px-4 py-4">
          <div className="flex items-center gap-3 rounded-xl px-2 py-2">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-to text-sm font-bold text-white">
              {name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-base font-semibold text-ink">{name}</div>
              <div className="text-sm text-ink-faint">{ROLE_LABEL[role]}</div>
            </div>
            <button
              onClick={signOut}
              className="shrink-0 rounded-lg p-2 text-ink-faint transition-colors hover:bg-stop-bg hover:text-stop"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1 px-10 py-10">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  )
}
