import { clearSession, getSession } from './session'
import type { MachineSummary } from './types'

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, options)
  if (!res.ok) throw new Error(`${path}: ${await res.text()}`)
  return (await res.json()) as T
}

export function authHeaders(): HeadersInit {
  const token = getSession()?.token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** api() with the session token attached; an expired session clears itself and returns home. */
export async function apiAuth<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  })
  if (res.status === 401) {
    clearSession()
    window.location.hash = '#/'
    throw new Error('session expired')
  }
  if (!res.ok) throw new Error(`${path}: ${await res.text()}`)
  return res.status === 204 ? (null as T) : ((await res.json()) as T)
}

export async function getMachine(machineId: string | number): Promise<MachineSummary> {
  const machines = await api<MachineSummary[]>('/api/machines')
  const machine = machines.find((m) => m.id === Number(machineId))
  if (!machine) throw new Error(`machine ${machineId} not found`)
  return machine
}
