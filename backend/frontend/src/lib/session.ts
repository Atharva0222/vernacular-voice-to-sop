import type { Role } from './types'

export interface Session {
  token: string
  name: string
  role: Role
}

const SESSION_KEY = 'v2sSession'

export function getSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function saveSession(data: Session): void {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data))
  } catch {
    // Storage blocked: worker pages never read a session anyway, so this is non-fatal.
  }
}

export function clearSession(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore
  }
}

export function signOut(): void {
  clearSession()
  window.location.hash = '#/'
}

/** The page a role belongs on after signing in. */
export function homeFor(role: Role): string {
  return role === 'supervisor' ? '/machines' : '/inbox'
}
