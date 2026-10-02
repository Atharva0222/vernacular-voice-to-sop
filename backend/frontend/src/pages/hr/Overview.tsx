import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Calendar, Check, Plus, Upload, X } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { BackLink, PageHeader, Shell, WhoAmI } from '../../components/layout'
import { StaffNav } from '../../components/StaffNav'
import { Badge, Button, EmptyState, Field, Select } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { apiAuth } from '../../lib/api'
import { useRequireRole } from '../../hooks/useSession'
import type {
  Application,
  Candidate,
  JobPosting,
  LeaveBalance,
  LeaveRequest,
  LeaveType,
} from '../../lib/types'

const STAGE_LABEL: Record<Application['stage'], string> = {
  applied: 'Applied',
  screening: 'Screening',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  hired: 'Hired',
}
const STAGE_ORDER: Application['stage'][] = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']

export default function Overview() {
  const staff = useRequireRole('supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter')
  const toast = useToast()
  const queryClient = useQueryClient()
  const isApprover = staff?.role === 'hr_admin' || staff?.role === 'plant_head'
  const isRecruiting = staff?.role === 'hr_admin' || staff?.role === 'recruiter' || staff?.role === 'plant_head'

  const [leaveTypeId, setLeaveTypeId] = useState('')
  const [startsOn, setStartsOn] = useState('')
  const [endsOn, setEndsOn] = useState('')
  const [requesting, setRequesting] = useState(false)

  const [addingPosting, setAddingPosting] = useState(false)
  const [postingTitle, setPostingTitle] = useState('')
  const [addingCandidate, setAddingCandidate] = useState(false)
  const [candidateName, setCandidateName] = useState('')
  const [resumeFile, setResumeFile] = useState<File | null>(null)

  const leaveTypesQuery = useQuery({ queryKey: ['leave-types'], queryFn: () => apiAuth<LeaveType[]>('/api/leave-types'), enabled: !!staff })
  const myBalancesQuery = useQuery({
    queryKey: ['leave-balances', 'me'],
    queryFn: () => apiAuth<LeaveBalance[]>('/api/leave-balances'),
    enabled: !!staff,
  })
  const myRequestsQuery = useQuery({
    queryKey: ['leave-requests'],
    queryFn: () => apiAuth<LeaveRequest[]>('/api/leave-requests'),
    enabled: !!staff,
  })
  const pendingQuery = useQuery({
    queryKey: ['leave-requests', 'pending'],
    queryFn: () => apiAuth<LeaveRequest[]>('/api/leave-requests?status=pending'),
    enabled: !!isApprover,
  })
  const postingsQuery = useQuery({
    queryKey: ['job-postings'],
    queryFn: () => apiAuth<JobPosting[]>('/api/job-postings'),
    enabled: !!isRecruiting,
  })
  const candidatesQuery = useQuery({
    queryKey: ['candidates'],
    queryFn: () => apiAuth<Candidate[]>('/api/candidates'),
    enabled: !!isRecruiting,
  })
  const applicationsQuery = useQuery({
    queryKey: ['applications'],
    queryFn: () => apiAuth<Application[]>('/api/applications'),
    enabled: !!isRecruiting,
  })

  async function submitLeaveRequest(e: FormEvent) {
    e.preventDefault()
    if (!leaveTypeId || !startsOn || !endsOn) return
    setRequesting(true)
    try {
      await apiAuth<LeaveRequest>('/api/leave-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leave_type_id: Number(leaveTypeId), starts_on: startsOn, ends_on: endsOn }),
      })
      setStartsOn('')
      setEndsOn('')
      await queryClient.invalidateQueries({ queryKey: ['leave-requests'] })
      toast('success', 'Leave requested.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not submit that request.')
    } finally {
      setRequesting(false)
    }
  }

  async function decide(requestId: number, decision: 'approve' | 'reject') {
    try {
      await apiAuth<LeaveRequest>(`/api/leave-requests/${requestId}/${decision}`, { method: 'POST' })
      await queryClient.invalidateQueries({ queryKey: ['leave-requests'] })
      await queryClient.invalidateQueries({ queryKey: ['leave-balances'] })
      toast('success', decision === 'approve' ? 'Approved.' : 'Rejected.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not record that decision.')
    }
  }

  async function submitPosting(e: FormEvent) {
    e.preventDefault()
    if (!postingTitle.trim()) return
    try {
      await apiAuth<JobPosting>('/api/job-postings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: postingTitle.trim() }),
      })
      setPostingTitle('')
      setAddingPosting(false)
      await queryClient.invalidateQueries({ queryKey: ['job-postings'] })
      toast('success', 'Job posting added.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not add that posting.')
    }
  }

  async function submitCandidate(e: FormEvent) {
    e.preventDefault()
    if (!candidateName.trim()) return
    try {
      const candidate = await apiAuth<Candidate>('/api/candidates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: candidateName.trim() }),
      })
      if (resumeFile) {
        const { upload_url, storage_path } = await apiAuth<{ upload_url: string; storage_path: string }>(
          `/api/candidates/${candidate.id}/resume-upload-url`,
          { method: 'POST' },
        )
        const uploadRes = await fetch(upload_url, {
          method: 'PUT',
          headers: { 'Content-Type': resumeFile.type || 'application/octet-stream' },
          body: resumeFile,
        })
        if (!uploadRes.ok) throw new Error('Resume upload failed')
        await apiAuth<Candidate>(`/api/candidates/${candidate.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resume_storage_path: storage_path }),
        })
      }
      setCandidateName('')
      setResumeFile(null)
      setAddingCandidate(false)
      await queryClient.invalidateQueries({ queryKey: ['candidates'] })
      toast('success', 'Candidate added.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not add that candidate.')
    }
  }

  async function applyToPosting(jobPostingId: number, candidateId: number) {
    try {
      await apiAuth<Application>('/api/applications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_posting_id: jobPostingId, candidate_id: candidateId }),
      })
      await queryClient.invalidateQueries({ queryKey: ['applications'] })
      toast('success', 'Application created.')
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not create that application.')
    }
  }

  async function advanceStage(applicationId: number, stage: Application['stage']) {
    try {
      await apiAuth<Application>(`/api/applications/${applicationId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage }),
      })
      await queryClient.invalidateQueries({ queryKey: ['applications'] })
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not update that application.')
    }
  }

  if (!staff) return null

  return (
    <Shell wide>
      <BackLink to="/">Home</BackLink>

      <PageHeader
        title="HR"
        subtitle="Leave requests and, for HR/recruiting roles, the hiring pipeline."
        right={
          <div className="flex items-center gap-3">
            <StaffNav role={staff.role} />
            <WhoAmI name={staff.name} role={staff.role} />
          </div>
        }
      />

      <section className="mb-10">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-ink">
          <Calendar size={18} /> My leave
        </h2>
        <div className="mb-4 flex flex-wrap gap-2">
          {myBalancesQuery.data?.length ? (
            myBalancesQuery.data.map((b) => {
              const type = leaveTypesQuery.data?.find((t) => t.id === b.leave_type_id)
              return (
                <Badge key={`${b.leave_type_id}-${b.year}`} variant="primary">
                  {type?.name ?? `Type ${b.leave_type_id}`}: {b.remaining_days} days left ({b.year})
                </Badge>
              )
            })
          ) : (
            <span className="text-sm text-ink-soft">No leave balance set for you yet.</span>
          )}
        </div>

        <form onSubmit={submitLeaveRequest} className="mb-5 flex flex-wrap items-end gap-3 rounded-3xl border border-border bg-white p-5 shadow-sm">
          <Select value={leaveTypeId} onChange={(e) => setLeaveTypeId(e.target.value)} required>
            <option value="" disabled>
              Leave type
            </option>
            {leaveTypesQuery.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
          <Field type="date" required value={startsOn} onChange={(e) => setStartsOn(e.target.value)} className="w-auto" />
          <Field type="date" required value={endsOn} onChange={(e) => setEndsOn(e.target.value)} className="w-auto" />
          <Button type="submit" size="sm" loading={requesting}>
            Request leave
          </Button>
        </form>

        {myRequestsQuery.data?.length ? (
          <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
            <table className="w-full text-sm">
              <tbody>
                {myRequestsQuery.data.map((r) => (
                  <tr key={r.id} className="border-b border-border last:border-0">
                    <td className="px-5 py-3 font-medium text-ink">{r.leave_type_name}</td>
                    <td className="px-5 py-3 text-ink-soft">
                      {r.starts_on} → {r.ends_on}
                    </td>
                    <td className="px-5 py-3">
                      <Badge variant={r.status === 'approved' ? 'safe' : r.status === 'rejected' ? 'stop' : 'caution'}>
                        {r.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={Calendar} title="No leave requests yet" />
        )}
      </section>

      {isApprover && (
        <section className="mb-10">
          <h2 className="mb-3 text-lg font-bold text-ink">Pending approvals</h2>
          {pendingQuery.data?.length ? (
            <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
              <table className="w-full text-sm">
                <tbody>
                  {pendingQuery.data.map((r) => (
                    <tr key={r.id} className="border-b border-border last:border-0">
                      <td className="px-5 py-3 font-medium text-ink">{r.employee_name}</td>
                      <td className="px-5 py-3 text-ink-soft">{r.leave_type_name}</td>
                      <td className="px-5 py-3 text-ink-soft">
                        {r.starts_on} → {r.ends_on}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex gap-2">
                          <Button size="sm" variant="success" onClick={() => decide(r.id, 'approve')}>
                            <Check size={14} />
                          </Button>
                          <Button size="sm" variant="danger" onClick={() => decide(r.id, 'reject')}>
                            <X size={14} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={Check} title="Nothing waiting on you" />
          )}
        </section>
      )}

      {isRecruiting && (
        <section>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-ink">
            <Briefcase size={18} /> Recruitment
          </h2>

          <div className="mb-5 rounded-3xl border border-border bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-bold text-ink">Job postings</h3>
              {!addingPosting && (
                <Button size="sm" variant="secondary" onClick={() => setAddingPosting(true)}>
                  <Plus size={14} /> New posting
                </Button>
              )}
            </div>
            <div className="mb-3 flex flex-wrap gap-2">
              {postingsQuery.data?.length ? (
                postingsQuery.data.map((p) => (
                  <Badge key={p.id} variant={p.status === 'open' ? 'safe' : 'neutral'}>
                    {p.title}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-ink-soft">No postings yet.</span>
              )}
            </div>
            {addingPosting && (
              <form onSubmit={submitPosting} className="flex flex-wrap gap-3 border-t border-border pt-3">
                <Field
                  required
                  placeholder="Title, e.g. Line Operator"
                  value={postingTitle}
                  onChange={(e) => setPostingTitle(e.target.value)}
                  className="min-w-[200px] flex-1"
                />
                <Button type="submit" size="sm">
                  Add
                </Button>
              </form>
            )}
          </div>

          <div className="mb-5 rounded-3xl border border-border bg-white p-5 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-bold text-ink">Candidates</h3>
              {!addingCandidate && (
                <Button size="sm" variant="secondary" onClick={() => setAddingCandidate(true)}>
                  <Plus size={14} /> New candidate
                </Button>
              )}
            </div>
            <div className="mb-3 flex flex-col gap-2">
              {candidatesQuery.data?.length ? (
                candidatesQuery.data.map((c) => (
                  <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium text-ink">
                      {c.name} {c.resume_storage_path && <Badge variant="info">resume on file</Badge>}
                    </span>
                    {postingsQuery.data?.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => applyToPosting(p.id, c.id)}
                        className="rounded-full border border-border px-2.5 py-1 text-xs font-semibold text-ink-soft hover:border-primary hover:text-primary-dark"
                      >
                        Apply to {p.title}
                      </button>
                    ))}
                  </div>
                ))
              ) : (
                <span className="text-sm text-ink-soft">No candidates yet.</span>
              )}
            </div>
            {addingCandidate && (
              <form onSubmit={submitCandidate} className="flex flex-wrap items-center gap-3 border-t border-border pt-3">
                <Field
                  required
                  placeholder="Full name"
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  className="min-w-[160px] flex-1"
                />
                <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-border-strong px-3 py-2 text-sm text-ink-soft hover:border-primary">
                  <Upload size={14} />
                  {resumeFile ? resumeFile.name : 'Resume (optional)'}
                  <input
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <Button type="submit" size="sm">
                  Add
                </Button>
              </form>
            )}
          </div>

          <div className="rounded-3xl border border-border bg-white p-5 shadow-sm">
            <h3 className="mb-3 text-sm font-bold text-ink">Applications</h3>
            {applicationsQuery.data?.length ? (
              <div className="flex flex-col gap-2">
                {applicationsQuery.data.map((a) => (
                  <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium text-ink">{a.candidate_name}</span>
                    <Select
                      value={a.stage}
                      onChange={(e) => advanceStage(a.id, e.target.value as Application['stage'])}
                      className="w-auto"
                    >
                      {STAGE_ORDER.map((s) => (
                        <option key={s} value={s}>
                          {STAGE_LABEL[s]}
                        </option>
                      ))}
                    </Select>
                  </div>
                ))}
              </div>
            ) : (
              <span className="text-sm text-ink-soft">No applications yet.</span>
            )}
          </div>
        </section>
      )}
    </Shell>
  )
}
