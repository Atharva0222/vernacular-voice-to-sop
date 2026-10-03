import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Briefcase, Clock, FileWarning, Users } from 'lucide-react'
import { AppShell } from '../components/AppShell'
import { CountBarChart, type CountBarDatum } from '../components/charts/CountBarChart'
import { StatTile } from '../components/charts/StatTile'
import { apiAuth } from '../lib/api'
import { useRequireRole } from '../hooks/useSession'
import { CHART_BAR_COLOR, STATUS_CRITICAL } from '../lib/chartColors'
import type {
  Application,
  ApplicationStage,
  EmployeeRole,
  EmployeeSummary,
  JobPosting,
  LeaveRequest,
  Report,
  ReportKind,
  ReportStatus,
  ShiftAssignment,
} from '../lib/types'

const STATUS_LABEL: Record<ReportStatus, string> = {
  received: 'Still processing',
  open: 'Open',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
  failed: 'Failed',
}
const KIND_LABEL: Record<ReportKind, string> = {
  machine: 'Machine fault',
  sop: 'Card is wrong',
  understanding: 'Needs training',
}
const ROLE_LABEL: Record<EmployeeRole, string> = {
  worker: 'Worker',
  supervisor: 'Supervisor',
  manager: 'Manager',
  plant_head: 'Plant Head',
  hr_admin: 'HR Admin',
  recruiter: 'Recruiter',
}
const STAGE_LABEL: Record<ApplicationStage, string> = {
  applied: 'Applied',
  screening: 'Screening',
  interview: 'Interview',
  offer: 'Offer',
  hired: 'Hired',
  rejected: 'Rejected',
}
const STAGE_ORDER: ApplicationStage[] = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']

function countBy<T, K extends string>(items: T[], key: (item: T) => K, labels: Record<K, string>, order?: K[]): CountBarDatum[] {
  const counts = {} as Record<K, number>
  for (const item of items) {
    const k = key(item)
    counts[k] = (counts[k] ?? 0) + 1
  }
  const keys = order ?? (Object.keys(counts) as K[])
  return keys
    .filter((k) => counts[k] > 0)
    .map((k) => ({ label: labels[k], value: counts[k] }))
    .sort((a, b) => (order ? 0 : b.value - a.value))
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function Dashboard() {
  const staff = useRequireRole('supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter')
  const isReportReader = staff?.role === 'manager' || staff?.role === 'plant_head'
  const isRecruiting = staff?.role === 'hr_admin' || staff?.role === 'recruiter' || staff?.role === 'plant_head'
  const hasLineAccess = staff?.role === 'supervisor' || staff?.role === 'manager' || staff?.role === 'plant_head'

  const employeesQuery = useQuery({
    queryKey: ['employees'],
    queryFn: () => apiAuth<EmployeeSummary[]>('/api/employees'),
    enabled: !!staff,
  })
  const reportsQuery = useQuery({
    queryKey: ['reports'],
    queryFn: () => apiAuth<Report[]>('/api/reports'),
    enabled: !!isReportReader,
  })
  const leaveQuery = useQuery({
    queryKey: ['leave-requests', 'pending'],
    queryFn: () => apiAuth<LeaveRequest[]>('/api/leave-requests?status=pending'),
    enabled: !!staff,
  })
  const shiftsQuery = useQuery({
    queryKey: ['shift-assignments', 'today'],
    queryFn: () => apiAuth<ShiftAssignment[]>(`/api/shift-assignments?work_date=${todayIso()}`),
    enabled: !!hasLineAccess,
  })
  const postingsQuery = useQuery({
    queryKey: ['job-postings'],
    queryFn: () => apiAuth<JobPosting[]>('/api/job-postings'),
    enabled: !!isRecruiting,
  })
  const applicationsQuery = useQuery({
    queryKey: ['applications'],
    queryFn: () => apiAuth<Application[]>('/api/applications'),
    enabled: !!isRecruiting,
  })

  if (!staff) return null

  const reports = reportsQuery.data ?? []
  const openReports = reports.filter((r) => r.status === 'open' || r.status === 'acknowledged').length
  const escalated = reports.filter((r) => r.escalated).length
  const openPostings = (postingsQuery.data ?? []).filter((p) => p.status === 'open').length

  return (
    <AppShell role={staff.role} name={staff.name}>
      <header className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">Dashboard</h1>
        <p className="mt-2 text-lg text-ink-soft">
          Welcome back, {staff.name.split(' ')[0]} — here's what's happening across your plant.
        </p>
      </header>

      <div className="mb-10 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {isReportReader && (
          <StatTile label="Open reports" value={openReports} icon={FileWarning} accent={openReports > 0 ? 'neutral' : 'good'} />
        )}
        {isReportReader && (
          <StatTile label="Escalated" value={escalated} icon={AlertTriangle} accent={escalated > 0 ? 'critical' : 'good'} />
        )}
        <StatTile label="Pending leave" value={leaveQuery.data?.length ?? 0} icon={Clock} />
        {hasLineAccess && <StatTile label="Shifts today" value={shiftsQuery.data?.length ?? 0} icon={Clock} />}
        <StatTile label="Employees" value={employeesQuery.data?.length ?? 0} icon={Users} />
        {isRecruiting && <StatTile label="Open postings" value={openPostings} icon={Briefcase} />}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {isReportReader && (
          <section className="rounded-2xl border border-border bg-white p-6 shadow-xs">
            <h2 className="mb-1 text-lg font-bold text-ink">Reports by status</h2>
            <p className="mb-4 text-sm text-ink-soft">Across every line you can see.</p>
            {reports.length === 0 ? (
              <p className="py-8 text-center text-sm text-ink-faint">No reports yet.</p>
            ) : (
              <CountBarChart
                data={countBy(reports, (r) => r.status, STATUS_LABEL).map((d) =>
                  d.label === STATUS_LABEL.open ? { ...d, color: STATUS_CRITICAL } : d,
                )}
              />
            )}
          </section>
        )}

        {isReportReader && (
          <section className="rounded-2xl border border-border bg-white p-6 shadow-xs">
            <h2 className="mb-1 text-lg font-bold text-ink">Reports by kind</h2>
            <p className="mb-4 text-sm text-ink-soft">What workers are telling you.</p>
            {reports.length === 0 ? (
              <p className="py-8 text-center text-sm text-ink-faint">No reports yet.</p>
            ) : (
              <CountBarChart data={countBy(reports.filter((r) => r.kind), (r) => r.kind as ReportKind, KIND_LABEL)} />
            )}
          </section>
        )}

        <section className="rounded-2xl border border-border bg-white p-6 shadow-xs">
          <h2 className="mb-1 text-lg font-bold text-ink">Employees by role</h2>
          <p className="mb-4 text-sm text-ink-soft">Everyone on the books at this plant.</p>
          {!employeesQuery.data?.length ? (
            <p className="py-8 text-center text-sm text-ink-faint">No employees yet.</p>
          ) : (
            <CountBarChart data={countBy(employeesQuery.data, (e) => e.role, ROLE_LABEL)} />
          )}
        </section>

        {isRecruiting && (
          <section className="rounded-2xl border border-border bg-white p-6 shadow-xs">
            <h2 className="mb-1 text-lg font-bold text-ink">Applications by stage</h2>
            <p className="mb-4 text-sm text-ink-soft">The hiring pipeline, left to right.</p>
            {!applicationsQuery.data?.length ? (
              <p className="py-8 text-center text-sm text-ink-faint">No applications yet.</p>
            ) : (
              <CountBarChart
                data={countBy(applicationsQuery.data, (a) => a.stage, STAGE_LABEL, STAGE_ORDER).map((d, i, arr) => ({
                  ...d,
                  color: d.label === STAGE_LABEL.rejected ? STATUS_CRITICAL : interpolateBlue(i, arr.length),
                }))}
              />
            )}
          </section>
        )}
      </div>
    </AppShell>
  )
}

// Lightest -> darkest across the funnel's natural order, so the narrowing pipeline reads at a
// glance even before anyone looks at the numbers (an ordinal sequential ramp, per the dataviz
// skill - not a categorical hue per stage).
function interpolateBlue(index: number, total: number): string {
  const steps = ['#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95']
  const i = Math.min(steps.length - 1, Math.round((index / Math.max(1, total - 1)) * (steps.length - 1)))
  return steps[i] ?? CHART_BAR_COLOR
}
