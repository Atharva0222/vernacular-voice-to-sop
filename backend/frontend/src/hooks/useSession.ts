import { useEffect, useSyncExternalStore } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSession, subscribeSession, type Session } from '../lib/session'
import type { Role } from '../lib/types'

/** `undefined` while Supabase's own (async) session hydration is still in flight, `null` once
 * resolved to "signed out". Pages that only need a truthy check treat both the same. */
export function useSession(): Session | null | undefined {
  return useSyncExternalStore(subscribeSession, getSession)
}

/** Redirects to sign-in once resolved to no session (or the wrong role) - never during the
 * brief `undefined` window, so refreshing a page never bounces an already-signed-in user. */
export function useRequireRole(...roles: Role[]): Session | null {
  const navigate = useNavigate()
  const session = useSession()

  useEffect(() => {
    if (session === undefined) return
    if (!session || !roles.includes(session.role)) {
      navigate('/', { replace: true })
    }
    // roles is a rest param of primitives passed fresh each render; session identity is stable per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, navigate])

  if (!session || !roles.includes(session.role)) return null
  return session
}
