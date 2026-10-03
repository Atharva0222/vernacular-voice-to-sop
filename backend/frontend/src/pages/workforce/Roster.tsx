import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock, LogIn, LogOut, Plus, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { AppShell } from '../../components/AppShell'
import { PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Field, Select, Spinner } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { apiAuth } from '../../lib/api'
import { useRequireRole } from '../../hooks/useSession'
import type { Attendance, EmployeeSummary, Line, Shift, ShiftAssignment } from '../../lib/types'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function Roster() {
  const staff = useRequireRole('supervisor', 'manager', 'plant_head', 'hr_admin')
  const toast = useToast()
  const queryClient = useQueryClient()
  const canManageShifts = staff?.role === 'hr_admin' || staff?.role === 'plant_head'

  const [workDate, setWorkDate] = useState(todayIso())
  const [assigning, setAssigning] = useState(false)
  const [assignEmployee, setAssignEmployee] = useState('')
  const [assignShift, setAssignShift] = useState('')
  const [assignLine, setAssignLine] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [addingShift, setAddingShift] = useState(false)
  const [newShiftName, setNewShiftName] = useState('')
  const [newShiftStart, setNewShiftStart] = useState('06:00')
  const [newShiftEnd, setNewShiftEnd] = useState('14:00')
  const [shiftSubmitting, setShiftSubmitting] = useState(false)
  // assignment id -> in-progress attendance id, tracked client-side for this session only
  // (there is no GET /attendance listing yet, so a page refresh loses "already clocked in").
  const [clockedIn, setClockedIn] = useState<Record<number, number>>({})

  const linesQuery = useQuery({ queryKey: ['lines'], queryFn: () => apiAuth<Line[]>('/api/lines'), enabled: !!staff })
  const shiftsQuery = useQuery({ queryKey: ['shifts'], queryFn: () => apiAuth<Shift[]>('/api/shifts'), enabled: !!staff })
  const workersQuery = useQuery({
    queryKey: ['employees', 'worker'],
    queryFn: () => apiAuth<EmployeeSummary[]>('/api/employees'),
    enabled: !!staff,
  })
  const assignmentsQuery = useQuery({
    queryKey: ['shift-assignments', workDate],
    queryFn: () => apiAuth<ShiftAssignment[]>(`/api/shift-assignments?work_date=${workDate}`),
    enabled: !!staff,
  })

  const hasLines = (linesQuery.data?.length ?? 0) > 0

  async function submitAssignment(e: FormEvent) {
    e.preventDefault()
    if (!assignEmployee || !assignShift || !assignLine) return
    setSubmitting(true)
    try {
      await apiAuth<ShiftAssignment>('/api/shift-assignments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: Number(assignEmployee),
          shift_id: Number(assignShift),
          line_id: Number(assignLine),
          work_date: workDate,
        }),
      })
      setAssigning(false)
      setAssignEmployee('')
      await queryClient.invalidateQueries({ queryKey: ['shift-assignments'] })
      toast('success', 'Shift assigned.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not assign that shift.')
    } finally {
      setSubmitting(false)
    }
  }

  async function clockIn(assignmentId: number) {
    try {
      const att = await apiAuth<Attendance>('/api/attendance/clock-in', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shift_assignment_id: assignmentId }),
      })
      setClockedIn((prev) => ({ ...prev, [assignmentId]: att.id }))
      toast('success', 'Clocked in.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not clock in.')
    }
  }

  async function clockOut(assignmentId: number) {
    const attendanceId = clockedIn[assignmentId]
    if (!attendanceId) return
    try {
      await apiAuth<Attendance>(`/api/attendance/${attendanceId}/clock-out`, { method: 'POST' })
      setClockedIn((prev) => {
        const next = { ...prev }
        delete next[assignmentId]
        return next
      })
      toast('success', 'Clocked out.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not clock out.')
    }
  }

  async function submitNewShift(e: FormEvent) {
    e.preventDefault()
    if (!newShiftName.trim()) return
    setShiftSubmitting(true)
    try {
      await apiAuth<Shift>('/api/shifts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newShiftName.trim(), starts_at: `${newShiftStart}:00`, ends_at: `${newShiftEnd}:00` }),
      })
      setNewShiftName('')
      setAddingShift(false)
      await queryClient.invalidateQueries({ queryKey: ['shifts'] })
      toast('success', `${newShiftName.trim()} shift added.`)
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not add that shift.')
    } finally {
      setShiftSubmitting(false)
    }
  }

  if (!staff) return null

  return (
    <AppShell role={staff.role} name={staff.name}>
      <PageHeader
        title="Workforce"
        subtitle="Shift assignments and clock-in/out for your lines. A supervisor runs the clock on behalf of the worker at a shared device - workers never sign in."
      />

      {canManageShifts && (
        <div className="mb-8 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-bold text-ink">Shift definitions</h2>
            {!addingShift && (
              <Button size="sm" variant="secondary" onClick={() => setAddingShift(true)}>
                <Plus size={14} /> New shift
              </Button>
            )}
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {shiftsQuery.data?.length ? (
              shiftsQuery.data.map((s) => (
                <Badge key={s.id} variant="neutral">
                  {s.name} ({s.starts_at}-{s.ends_at})
                </Badge>
              ))
            ) : (
              <span className="text-sm text-ink-soft">No shifts defined yet.</span>
            )}
          </div>
          {addingShift && (
            <form onSubmit={submitNewShift} className="flex flex-wrap items-end gap-3 border-t border-border pt-4">
              <Field
                required
                placeholder="Name, e.g. Morning"
                value={newShiftName}
                onChange={(e) => setNewShiftName(e.target.value)}
                className="min-w-[160px] flex-1"
              />
              <Field type="time" required value={newShiftStart} onChange={(e) => setNewShiftStart(e.target.value)} className="w-auto" />
              <Field type="time" required value={newShiftEnd} onChange={(e) => setNewShiftEnd(e.target.value)} className="w-auto" />
              <Button type="submit" size="sm" loading={shiftSubmitting}>
                Add
              </Button>
              <button
                type="button"
                onClick={() => setAddingShift(false)}
                className="rounded-full p-1.5 text-ink-faint hover:bg-black/5 hover:text-ink"
              >
                <X size={16} />
              </button>
            </form>
          )}
        </div>
      )}

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Field type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} className="w-auto" />
      </div>

      {!hasLines && !canManageShifts && (
        <EmptyState
          icon={Clock}
          title="No lines of your own"
          subtitle="Only the supervisor or manager of a line (or a plant head) can schedule shifts on it."
        />
      )}

      {assignmentsQuery.isLoading && (
        <div className="flex items-center gap-2 py-10 text-ink-soft">
          <Spinner /> Loading roster...
        </div>
      )}

      {assignmentsQuery.isSuccess && assignmentsQuery.data.length === 0 && hasLines && (
        <EmptyState icon={Clock} title="Nothing scheduled for this date" subtitle="Assign a shift below." />
      )}

      {assignmentsQuery.isSuccess && assignmentsQuery.data.length > 0 && (
        <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-black/[0.02] text-left text-xs font-semibold uppercase tracking-wide text-ink-faint">
                <th className="px-5 py-3">Worker</th>
                <th className="px-5 py-3">Shift</th>
                <th className="px-5 py-3">Attendance</th>
              </tr>
            </thead>
            <tbody>
              {assignmentsQuery.data.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 font-medium text-ink">{a.employee_name}</td>
                  <td className="px-5 py-3">
                    <Badge variant="primary">{a.shift_name}</Badge>
                  </td>
                  <td className="px-5 py-3">
                    {clockedIn[a.id] ? (
                      <Button size="sm" variant="secondary" onClick={() => clockOut(a.id)}>
                        <LogOut size={14} /> Clock out
                      </Button>
                    ) : (
                      <Button size="sm" onClick={() => clockIn(a.id)}>
                        <LogIn size={14} /> Clock in
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hasLines && (
        <div className="mt-8">
          {!assigning ? (
            <button
              onClick={() => setAssigning(true)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border-strong bg-white/60 py-5 text-sm font-semibold text-ink-soft transition-colors hover:border-primary hover:text-primary-dark"
            >
              <Plus size={18} /> Assign a shift
            </button>
          ) : (
            <form onSubmit={submitAssignment} className="rounded-3xl border border-border bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-bold text-ink">Assign a shift for {workDate}</h2>
                <button
                  type="button"
                  onClick={() => setAssigning(false)}
                  className="rounded-full p-1 text-ink-faint hover:bg-black/5 hover:text-ink"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="flex flex-wrap gap-3">
                <Select value={assignEmployee} onChange={(e) => setAssignEmployee(e.target.value)} required>
                  <option value="" disabled>
                    Worker
                  </option>
                  {workersQuery.data?.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.name}
                    </option>
                  ))}
                </Select>
                <Select value={assignShift} onChange={(e) => setAssignShift(e.target.value)} required>
                  <option value="" disabled>
                    Shift
                  </option>
                  {shiftsQuery.data?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.starts_at}-{s.ends_at})
                    </option>
                  ))}
                </Select>
                <Select value={assignLine} onChange={(e) => setAssignLine(e.target.value)} required>
                  <option value="" disabled>
                    Line
                  </option>
                  {linesQuery.data?.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name}
                    </option>
                  ))}
                </Select>
                <Button type="submit" loading={submitting}>
                  Assign
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </AppShell>
  )
}
