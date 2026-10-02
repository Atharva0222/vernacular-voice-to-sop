import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Check, Inbox as InboxIcon, X } from 'lucide-react'
import { useState } from 'react'
import { BackLink, PageHeader, Shell, WhoAmI } from '../components/layout'
import { StaffNav } from '../components/StaffNav'
import { Badge, Button, EmptyState, Field, Select, Spinner } from '../components/ui'
import { useToast } from '../components/Toast'
import { apiAuth } from '../lib/api'
import { useRequireRole } from '../hooks/useSession'
import type { Report, ReportKind, ReportStatus, StepEdit } from '../lib/types'

const KIND_LABEL: Record<ReportKind, string> = {
  machine: 'Machine fault',
  sop: 'Card is wrong',
  understanding: 'Needs training',
}
const KIND_VARIANT: Record<ReportKind, 'info' | 'violet' | 'caution'> = {
  machine: 'info',
  sop: 'violet',
  understanding: 'caution',
}
const STATUS_LABEL: Record<ReportStatus, string> = {
  open: 'Open',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
  received: 'Still processing',
  failed: 'Failed',
}

export default function Inbox() {
  const staff = useRequireRole('manager', 'plant_head')
  const toast = useToast()
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('')
  const [kind, setKind] = useState('')

  const reportsQuery = useQuery({
    queryKey: ['reports', status, kind],
    queryFn: () => {
      const p = new URLSearchParams()
      if (status) p.set('status', status)
      if (kind) p.set('kind', kind)
      return apiAuth<Report[]>(`/api/reports?${p}`)
    },
    enabled: !!staff,
  })

  const editsQuery = useQuery({
    queryKey: ['step-edits'],
    queryFn: () => apiAuth<StepEdit[]>('/api/step-edits'),
    enabled: !!staff,
  })

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['reports'] })
    queryClient.invalidateQueries({ queryKey: ['step-edits'] })
  }

  if (!staff) return null

  return (
    <Shell wide>
      <BackLink to="/">Home</BackLink>

      <PageHeader
        title="Worker reports"
        subtitle="What the cards could not answer, in the words of the people running your lines. No names are attached, and the recordings are gone."
        right={
          <div className="flex items-center gap-3">
            <StaffNav role={staff.role} />
            <WhoAmI name={staff.name} role={staff.role} />
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap gap-3">
        <Select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Any status</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="received">Still processing</option>
          <option value="failed">Failed</option>
        </Select>
        <Select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Any kind</option>
          <option value="machine">Machine fault</option>
          <option value="sop">Card is wrong</option>
          <option value="understanding">Needs training</option>
        </Select>
      </div>

      {editsQuery.data && editsQuery.data.length > 0 && (
        <div className="mb-8 flex flex-col gap-4">
          {editsQuery.data.map((e) => (
            <StepEditCard key={e.id} edit={e} onDone={refresh} notify={toast} />
          ))}
        </div>
      )}

      {reportsQuery.isLoading && (
        <div className="flex items-center gap-2 py-10 text-ink-soft">
          <Spinner /> Loading reports...
        </div>
      )}

      {reportsQuery.isError && (
        <p className="rounded-2xl bg-stop-bg px-4 py-3 text-sm font-medium text-stop">
          {(reportsQuery.error as Error).message}
        </p>
      )}

      {reportsQuery.data && reportsQuery.data.length === 0 && (
        <EmptyState
          icon={InboxIcon}
          title="Nothing waiting for you"
          subtitle="Reports appear here when a worker speaks about something the cards do not cover."
        />
      )}

      {reportsQuery.data && reportsQuery.data.length > 0 && (
        <div className="flex flex-col gap-4">
          {reportsQuery.data.map((r, i) => (
            <ReportCard key={r.id} report={r} index={i} onDone={refresh} notify={toast} />
          ))}
        </div>
      )}
    </Shell>
  )
}

type Notify = (kind: 'error' | 'success' | 'info', message: string) => void

function ReportCard({ report: r, index, onDone, notify }: { report: Report; index: number; onDone: () => void; notify: Notify }) {
  const [reply, setReply] = useState('')
  const [nextStatus, setNextStatus] = useState<string>(r.status === 'open' || r.status === 'acknowledged' || r.status === 'resolved' ? r.status : 'open')
  const [sending, setSending] = useState(false)
  const pending = r.status === 'received' || r.status === 'failed'
  const when = new Date(r.created_at).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })

  async function send() {
    setSending(true)
    try {
      await apiAuth(`/api/report/${r.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus, ...(reply.trim() && { response_text: reply.trim() }) }),
      })
      setReply('')
      notify('success', 'Reply sent.')
      onDone()
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Sending the reply failed.')
    } finally {
      setSending(false)
    }
  }

  const accent = r.kind ? { machine: 'border-l-info', sop: 'border-l-violet', understanding: 'border-l-caution' }[r.kind] : 'border-l-border-strong'

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.03 }}
      className={`rounded-3xl border border-border border-l-4 bg-white p-5 shadow-sm ${accent}`}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {r.kind && <Badge variant={KIND_VARIANT[r.kind]}>{KIND_LABEL[r.kind]}</Badge>}
        {r.severity === 'high' && <Badge variant="stop">Risk of injury</Badge>}
        <Badge variant="neutral">{STATUS_LABEL[r.status]}</Badge>
        {r.escalated && <Badge variant="stop">Now with the plant head</Badge>}
        {r.cluster_size > 1 && (
          <Badge variant={r.confirmed ? 'stop' : 'neutral'}>
            {r.confirmed ? 'Confirmed by' : 'Said by'} {r.cluster_size} workers
          </Badge>
        )}
        <span className="ml-auto text-xs tabular-nums text-ink-faint">
          {when} · report {r.id}
        </span>
      </div>

      <p className="lang-dev text-lg leading-snug text-ink" dir="auto">
        {r.summary || (r.status === 'failed' ? `Could not be processed: ${r.error}` : 'Being transcribed and sorted...')}
      </p>

      {r.suggested_change && (
        <div className="lang-dev mt-3 rounded-xl border-l-2 border-border-strong bg-canvas p-3 text-base" dir="auto">
          <b className="block font-sans text-xs font-semibold text-ink-soft">Suggested card text</b>
          {r.suggested_change}
        </div>
      )}
      {r.response_text && (
        <div className="lang-dev mt-3 rounded-xl border-l-2 border-primary/40 bg-primary-light p-3 text-base" dir="auto">
          <b className="block font-sans text-xs font-semibold text-primary-dark">You replied</b>
          {r.response_text}
        </div>
      )}

      {!pending && (
        <div className="mt-4 flex flex-wrap gap-2.5">
          <Field
            dir="auto"
            placeholder={`Reply to the worker, spoken back in ${r.language === 'mr' ? 'Marathi' : 'Hindi'}`}
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            className="min-w-[220px] flex-1"
          />
          <Select value={nextStatus} onChange={(e) => setNextStatus(e.target.value)}>
            <option value="open">Open</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="resolved">Resolved</option>
          </Select>
          <Button size="sm" loading={sending} onClick={send}>
            Send reply
          </Button>
        </div>
      )}
    </motion.article>
  )
}

function StepEditCard({ edit: e, onDone, notify }: { edit: StepEdit; onDone: () => void; notify: Notify }) {
  const [busy, setBusy] = useState(false)
  const who = e.report_count === 1 ? 'A worker says' : `${e.report_count} workers say`

  async function act(action: 'approve' | 'reject') {
    setBusy(true)
    try {
      await apiAuth(`/api/step-edit/${e.id}/${action}`, { method: 'POST' })
      notify('success', action === 'approve' ? 'Card updated.' : 'Kept as is.')
      onDone()
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'That did not go through.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-3xl border-2 border-ink bg-white p-5 shadow-sm"
    >
      <h2 className="mb-3 text-sm font-bold text-ink">
        {who} step {e.step_number} on machine {e.machine_id} is wrong
      </h2>
      <p className="lang-dev rounded-xl bg-stop-bg p-3 text-base text-stop line-through" dir="auto">
        {e.old_text}
      </p>
      <p className="lang-dev mt-2 rounded-xl bg-safe-bg p-3 text-base text-safe" dir="auto">
        {e.new_text}
      </p>
      <div className="mt-4 flex gap-2.5">
        <Button variant="success" size="sm" loading={busy} onClick={() => act('approve')}>
          <Check size={15} /> Change the card
        </Button>
        <Button variant="secondary" size="sm" disabled={busy} onClick={() => act('reject')}>
          <X size={15} /> Keep it as it is
        </Button>
      </div>
    </motion.article>
  )
}
