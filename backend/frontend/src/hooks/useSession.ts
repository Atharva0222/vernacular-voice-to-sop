import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSession, type Session } from '../lib/session'
import type { Role } from '../lib/types'

export function useSession(): Session | null {
  const [session] = useState(() => getSession())
  return session
}

/** Redirects to sign-in when there is no session or the role does not match. */
export function useRequireRole(...roles: Role[]): Session | null {
  const navigate = useNavigate()
  const session = useSession()

  useEffect(() => {
    if (!session || !roles.includes(session.role)) {
      navigate('/', { replace: true })
    }
    // roles is a rest param of primitives passed fresh each render; session identity is stable per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, navigate])

  if (!session || !roles.includes(session.role)) return null
  return session
}
