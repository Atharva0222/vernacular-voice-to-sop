import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Cog, Factory, Plus, X } from 'lucide-react'
import { type FormEvent, type ReactNode, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { BackLink, PageHeader, Shell } from '../components/layout'
import { Button, EmptyState, Field, Select, Spinner } from '../components/ui'
import { useToast } from '../components/Toast'
import { apiAuth } from '../lib/api'
import { useSession } from '../hooks/useSession'
import type { Line, MachineSummary } from '../lib/types'

async function fetchMachines(): Promise<MachineSummary[]> {
  const res = await fetch('/api/machines')
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export default function Machines() {
  const session = useSession()
  const toast = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isStaff = !!session
  const isSupervisor = session?.role === 'supervisor'
  const target = isSupervisor ? 'create' : 'cards'
  const [adding, setAdding] = useState(false)
  const [newName, setNewName] = useState('')
  const [newLine, setNewLine] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const machinesQuery = useQuery({ queryKey: ['machines'], queryFn: fetchMachines })
  const linesQuery = useQuery({
    queryKey: ['lines'],
    queryFn: () => apiAuth<Line[]>('/api/lines'),
    enabled: isSupervisor,
  })

  const ownLineIds = useMemo(() => linesQuery.data?.map((l) => l.id) ?? null, [linesQuery.data])

  const machines = useMemo(() => {
    const all = machinesQuery.data ?? []
    return isSupervisor && ownLineIds ? all.filter((m) => ownLineIds.includes(m.line_id)) : all
  }, [machinesQuery.data, isSupervisor, ownLineIds])

  // Keyed on isStaff, not isSupervisor: any signed-in staff member (manager, plant_head, HR...)
  // gets the English staff copy. Only a worker with no session at all sees the Hindi one.
  const WORDS = isStaff
    ? {
        title: 'Pick a machine',
        subtitle: 'Choose the machine you are recording a procedure for.',
        cards: (m: MachineSummary) => `${m.step_count} cards · v${m.sop_version}`,
        none: 'No cards yet',
        back: 'Home',
      }
    : {
        title: 'मशीन चुनें',
        subtitle: 'हर मशीन के अपने कार्ड हैं। अपनी मशीन चुनें।',
        cards: (m: MachineSummary) => `${m.step_count} कार्ड, संस्करण ${m.sop_version}`,
        none: 'अभी कोई कार्ड नहीं',
        back: 'होम',
      }

  async function submitNewMachine(e: FormEvent) {
    e.preventDefault()
    if (!newLine || !newName.trim()) return
    setSubmitting(true)
    try {
      const machine = await apiAuth<MachineSummary>('/api/machines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ line_id: Number(newLine), name: newName.trim() }),
      })
      setNewName('')
      setAdding(false)
      await queryClient.invalidateQueries({ queryKey: ['machines'] })
      toast('success', `${machine.name} added — opening the recorder...`)
      navigate(`/create?machine=${machine.id}`)
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Could not add the machine.')
    } finally {
      setSubmitting(false)
    }
  }

  const content = (
    <>
      <PageHeader title={WORDS.title} subtitle={WORDS.subtitle} devanagari={!isStaff} />

      {machinesQuery.isLoading && (
        <div className="flex items-center gap-2 py-10 text-ink-soft">
          <Spinner /> Loading machines...
        </div>
      )}

      {machinesQuery.isError && (
        <p className="rounded-2xl bg-stop-bg px-4 py-3 text-sm font-medium text-stop">
          {(machinesQuery.error as Error).message}
        </p>
      )}

      {machinesQuery.isSuccess && machines.length === 0 && (
        <EmptyState
          icon={Factory}
          title={isStaff ? 'No machines on your lines yet' : 'कोई मशीन उपलब्ध नहीं'}
          subtitle={isStaff ? 'Add one below to get started.' : undefined}
        />
      )}

      {machinesQuery.isSuccess && machines.length > 0 && (
        <div className="grid gap-5 sm:grid-cols-2">
          {machines.map((m, i) => {
            const hasSop = m.sop_id !== null
            return (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Link
                  to={`/${target}?machine=${m.id}`}
                  className="group relative block overflow-hidden rounded-3xl border border-border bg-white p-6 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg"
                >
                  <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full bg-gradient-to-br from-primary/8 to-primary-to/8 transition-transform duration-500 group-hover:scale-125" />
                  <div className="relative flex items-start justify-between gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary-to text-white shadow-sm">
                      <Cog size={20} />
                    </div>
                    <ArrowRight
                      size={18}
                      className="mt-2 text-ink-faint opacity-0 transition-all group-hover:translate-x-1 group-hover:opacity-100"
                    />
                  </div>
                  <h2 className={clsxTitle(!isStaff)}>{m.name}</h2>
                  <p className="mt-0.5 text-base text-ink-soft">{m.line_name}</p>
                  <span
                    className={`mt-4 inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${
                      hasSop ? 'bg-safe-bg text-safe' : 'bg-caution-bg text-caution'
                    }`}
                  >
                    {hasSop ? WORDS.cards(m) : WORDS.none}
                  </span>
                </Link>
              </motion.div>
            )
          })}
        </div>
      )}

      {isSupervisor && linesQuery.data && (
        <div className="mt-8">
          <AnimatePresence>
            {!adding ? (
              <motion.div key="toggle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <button
                  onClick={() => setAdding(true)}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border-strong bg-white/60 py-5 text-base font-semibold text-ink-soft transition-colors hover:border-primary hover:text-primary-dark"
                >
                  <Plus size={18} /> Add a machine
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="form"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
              >
                {/* Plain form/button, not motion.*: a motion element with an `exit` prop inside
                    AnimatePresence swallows the native click->submit default action. */}
                <form onSubmit={submitNewMachine} className="rounded-3xl border border-border bg-white p-6 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-bold text-ink">New machine</h2>
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
                      maxLength={60}
                      placeholder="Machine name, e.g. Drill 2"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="min-w-[200px] flex-1"
                    />
                    <Select value={newLine} onChange={(e) => setNewLine(e.target.value)} required>
                      <option value="" disabled>
                        Choose a line
                      </option>
                      {linesQuery.data.map((l) => (
                        <option key={l.id} value={l.id}>
                          {l.name}
                        </option>
                      ))}
                    </Select>
                    <Button type="submit" loading={submitting}>
                      Add machine
                    </Button>
                  </div>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </>
  )

  if (session) {
    return (
      <AppShell role={session.role} name={session.name}>
        {content}
      </AppShell>
    )
  }

  return (
    <Worker>
      <BackLink to="/">{WORDS.back}</BackLink>
      {content}
    </Worker>
  )
}

function Worker({ children }: { children: ReactNode }) {
  return (
    <div className="lang-dev">
      <Shell wide>{children}</Shell>
    </div>
  )
}

function clsxTitle(devanagari: boolean) {
  return devanagari ? 'lang-dev mt-4 text-2xl font-bold text-ink' : 'mt-4 text-xl font-bold text-ink'
}
