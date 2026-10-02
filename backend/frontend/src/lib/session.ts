import { supabase } from './supabase'
import type { Role } from './types'

export interface Session {
  token: string
  name: string
  role: Role
}

const SESSION_KEY = 'v2sSession'
type Listener = () => void

// `undefined` means "not resolved yet" (Supabase's own session hydration is async, even for an
// already-signed-in user) - distinct from `null`, which means "genuinely signed out". Callers
// that only care about "ready to use" treat both as falsy; useRequireRole cares about the
// difference so it doesn't bounce a valid session to the sign-in page during that first tick.
let cached: Session | null | undefined
const listeners = new Set<Listener>()

function setCached(next: Session | null): void {
  cached = next
  try {
    if (next) sessionStorage.setItem(SESSION_KEY, JSON.stringify(next))
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // Storage blocked: worker pages never read a session anyway, so this is non-fatal.
  }
  listeners.forEach((fn) => fn())
}

async function resolveFromSupabase(token: string): Promise<void> {
  try {
    const res = await fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } })
    if (!res.ok) throw new Error('no staff profile for this account')
    const me = (await res.json()) as { name: string; role: Role }
    setCached({ token, name: me.name, role: me.role })
  } catch {
    setCached(null)
  }
}

// Fires once immediately with whatever session Supabase already has persisted (or none), and
// again on every sign-in/sign-out/token-refresh - this is also what keeps `cached.token` fresh
// across Supabase's automatic background token refresh, with no extra code needed for that.
supabase.auth.onAuthStateChange((_event, authSession) => {
  if (authSession) void resolveFromSupabase(authSession.access_token)
  else setCached(null)
})

export function getSession(): Session | null | undefined {
  return cached
}

export function subscribeSession(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export async function signIn(email: string, password: string): Promise<Session> {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error || !data.session) throw new Error(error?.message ?? 'sign-in failed')
  const token = data.session.access_token
  const res = await fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new Error('Signed in, but this account has no staff profile.')
  const me = (await res.json()) as { name: string; role: Role }
  const session: Session = { token, name: me.name, role: me.role }
  setCached(session)
  return session
}

/** Drops the cached session without waiting on Supabase - used by apiAuth() on a 401 so an
 * expired/invalid token stops being sent immediately, not after an extra round trip. */
export function clearSession(): void {
  setCached(null)
}

export async function signOut(): Promise<void> {
  clearSession()
  await supabase.auth.signOut()
  window.location.hash = '#/'
}

/** The page a role belongs on after signing in. */
export function homeFor(role: Role): string {
  if (role === 'supervisor') return '/machines'
  if (role === 'manager' || role === 'plant_head') return '/inbox'
  if (role === 'recruiter') return '/hr'
  return '/employees'
}
