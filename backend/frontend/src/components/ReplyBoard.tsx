import { ChevronDown, MessageSquare, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { MachineReply } from '../lib/types'

const WORDS = {
  title: 'मैनेजर के जवाब',
  unheard: (n: number) => `${n} नया`,
  step: (n: number) => `कार्ड ${n} के बारे में`,
  empty: 'अभी कोई जवाब नहीं आया है।',
  play: 'सुनें',
}

/** Which replies this device has already played. Kept per machine in local storage: a worker
 * has no account to hang "seen" state off (see CLAUDE.md's Auth section), and a shared machine
 * tablet is the device the state belongs to anyway. */
function heardKey(machineId: string) {
  return `heardReplies:${machineId}`
}

function readHeard(machineId: string): number[] {
  try {
    return JSON.parse(localStorage.getItem(heardKey(machineId)) ?? '[]') as number[]
  } catch {
    return []
  }
}

function markHeard(machineId: string, id: number) {
  try {
    const next = Array.from(new Set([...readHeard(machineId), id]))
    localStorage.setItem(heardKey(machineId), JSON.stringify(next))
  } catch {
    // A private window or blocked site data just means the badge reappears; nothing breaks.
  }
}

/** The manager's answers for this machine, pulled rather than pushed, and never auto-played:
 * a worker who walks away and comes back finds the badge waiting, instead of being ambushed by
 * audio from a tab they left open. */
export function ReplyBoard({ machineId }: { machineId: string }) {
  const [replies, setReplies] = useState<MachineReply[] | null>(null)
  const [heard, setHeard] = useState<number[]>(() => readHeard(machineId))
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const rows = await api<MachineReply[]>(`/api/machine/${machineId}/replies`)
        if (!cancelled) setReplies(rows)
      } catch {
        // A failed reply fetch must never take the SOP cards down with it.
      }
    }
    void load()
    // Refresh when the worker comes back to the page, which is when a new answer is likely.
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [machineId])

  function play(reply: MachineReply) {
    new Audio(`/api/audio/${reply.audio_key}`).play().catch(() => {})
    markHeard(machineId, reply.id)
    setHeard((prev) => [...prev, reply.id])
  }

  if (!replies?.length) return null
  const unheard = replies.filter((r) => !heard.includes(r.id)).length

  return (
    <section className="mb-5 overflow-hidden rounded-3xl border border-border bg-white shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 p-4 text-left"
        aria-expanded={open}
      >
        <MessageSquare size={22} className="shrink-0 text-primary" />
        <span className="flex-1 text-lg font-semibold text-ink">{WORDS.title}</span>
        {unheard > 0 && (
          <span className="rounded-full bg-primary px-3 py-1 text-sm font-bold text-white">
            {WORDS.unheard(unheard)}
          </span>
        )}
        <ChevronDown size={20} className={`shrink-0 text-ink-faint transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <ul className="border-t border-border">
          {replies.map((reply) => (
            <li key={reply.id} className="flex items-start gap-3 border-b border-border p-4 last:border-b-0">
              <div className="flex-1">
                <p className="text-lg leading-snug text-ink" dir="auto">
                  {reply.text}
                </p>
                <p className="mt-1 text-xs text-ink-faint">
                  {new Date(reply.responded_at).toLocaleString(undefined, {
                    day: 'numeric',
                    month: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                  {reply.step_number !== null && ` · ${WORDS.step(reply.step_number)}`}
                </p>
              </div>
              <button
                onClick={() => play(reply)}
                aria-label={WORDS.play}
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-ink text-ink transition-colors hover:bg-ink hover:text-white"
              >
                <Play size={20} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
