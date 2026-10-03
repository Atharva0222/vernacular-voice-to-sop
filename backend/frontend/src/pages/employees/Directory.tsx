import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Plus, Users, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { AppShell } from '../../components/AppShell'
import { PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Field, Select, Spinner } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { apiAuth } from '../../lib/api'
import { useRequireRole } from '../../hooks/useSession'
import type { Department, EmployeeRole, EmployeeSummary } from '../../lib/types'

const ROLE_LABEL: Record<EmployeeRole, string> = {
  worker: 'Worker',
  supervisor: 'Supervisor',
  manager: 'Manager',
  plant_head: 'Plant Head',
  hr_admin: 'HR Admin',
  recruiter: 'Recruiter',
}

export default function Directory() {
  const staff = useRequireRole('supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter')
  const toast = useToast()
  const queryClient = useQueryClient()
  const canManage = staff?.role === 'hr_admin' || staff?.role === 'plant_head'

  const [departmentId, setDepartmentId] = useState('')
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [newRole, setNewRole] = useState<EmployeeRole>('worker')
  const [submitting, setSubmitting] = useState(false)

  const employeesQuery = useQuery({
    queryKey: ['employees', departmentId],
    queryFn: () => {
      const p = new URLSearchParams()
      if (departmentId) p.set('department_id', departmentId)
      return apiAuth<EmployeeSummary[]>(`/api/employees?${p}`)
    },
    enabled: !!staff,
  })

  const departmentsQuery = useQuery({
    queryKey: ['departments'],
    queryFn: () => apiAuth<Department[]>('/api/departments'),
    enabled: !!staff,
  })

  async function submitNewEmployee(e: FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setSubmitting(true)
    try {
      await apiAuth<EmployeeSummary>('/api/employees', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim(), role: newRole }),
      })
      setNewName('')
      setAdding(false)
      await queryClient.invalidateQueries({ queryKey: ['employees'] })
      toast('success', `${newName.trim()} added to the directory.`)
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not add that employee.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!staff) return null

  return (
    <AppShell role={staff.role} name={staff.name}>
      <PageHeader
        title="Employees"
        subtitle="Everyone on the books at this plant, from line workers tracked for scheduling to the staff who run it."
      />

      <div className="mb-6 flex flex-wrap gap-3">
        <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
          <option value="">Any department</option>
          {departmentsQuery.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>
      </div>

      {employeesQuery.isLoading && (
        <div className="flex items-center gap-2 py-10 text-ink-soft">
          <Spinner /> Loading employees...
        </div>
      )}

      {employeesQuery.isError && (
        <p className="rounded-2xl bg-stop-bg px-4 py-3 text-sm font-medium text-stop">
          {(employeesQuery.error as Error).message}
        </p>
      )}

      {employeesQuery.isSuccess && employeesQuery.data.length === 0 && (
        <EmptyState icon={Users} title="No one in the directory yet" subtitle="Add the first person below." />
      )}

      {employeesQuery.isSuccess && employeesQuery.data.length > 0 && (
        <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-black/[0.02] text-left text-xs font-semibold uppercase tracking-wide text-ink-faint">
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Job title</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {employeesQuery.data.map((emp) => (
                <tr key={emp.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 font-medium text-ink">{emp.name}</td>
                  <td className="px-5 py-3">
                    <Badge variant={emp.role === 'worker' ? 'neutral' : 'primary'}>{ROLE_LABEL[emp.role]}</Badge>
                  </td>
                  <td className="px-5 py-3 text-ink-soft">{emp.job_title ?? '—'}</td>
                  <td className="px-5 py-3">
                    <Badge variant={emp.employment_status === 'active' ? 'safe' : 'caution'}>
                      {emp.employment_status.replace('_', ' ')}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canManage && (
        <div className="mt-8">
          <AnimatePresence>
            {!adding ? (
              <motion.div key="toggle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <button
                  onClick={() => setAdding(true)}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border-strong bg-white/60 py-5 text-sm font-semibold text-ink-soft transition-colors hover:border-primary hover:text-primary-dark"
                >
                  <Plus size={18} /> Add an employee
                </button>
              </motion.div>
            ) : (
              <motion.div key="form" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                {/* Plain form/button, not motion.*: a motion element with an `exit` prop inside
                    AnimatePresence swallows the native click->submit default action. */}
                <form onSubmit={submitNewEmployee} className="rounded-3xl border border-border bg-white p-6 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-base font-bold text-ink">New employee</h2>
                    <button
                      type="button"
                      onClick={() => setAdding(false)}
                      className="rounded-full p-1 text-ink-faint hover:bg-black/5 hover:text-ink"
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Field
                      required
                      maxLength={120}
                      placeholder="Full name"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="min-w-[200px] flex-1"
                    />
                    <Select value={newRole} onChange={(e) => setNewRole(e.target.value as EmployeeRole)}>
                      {(Object.keys(ROLE_LABEL) as EmployeeRole[]).map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABEL[r]}
                        </option>
                      ))}
                    </Select>
                    <Button type="submit" loading={submitting}>
                      Add employee
                    </Button>
                  </div>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </AppShell>
  )
}
