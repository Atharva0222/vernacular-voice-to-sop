import { Play, Ticket } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { readReceipts } from '../lib/receipts'

const WORDS = {
  title: 'आपके सवाल का जवाब',
  waiting: 'मैनेजर का जवाब आने पर यहाँ दिखेगा।',
  play: 'सुनें',
}

type Answer = {
  receipt: string
  text: string
  audio_key: string
  responded_at: string | null
}

type ReceiptResponse = {
  status: string
  ack_audio_key: string | null
  answered_by_sop: boolean
  text: string | null
  responded_at: string | null
}

/** Replies to the questions THIS device asked, claimed with the receipts it holds.
 *
 * This is the private half of reply delivery: a 'machine' or 'sop' answer concerns everyone at
 * the machine and goes on the ReplyBoard, while an 'understanding' answer is meant for the one
 * worker who asked and reaches them only here. Still no account and no identity - the receipt
 * is a bearer ticket, not a name. Never auto-plays.
 */
export function MyAnswers({ machineId }: { machineId: string }) {
  const [answers, setAnswers] = useState<Answer[]>([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      const receipts = readReceipts(machineId)
      if (!receipts.length) return
      const settled = await Promise.all(
        receipts.map(async (receipt): Promise<Answer | null> => {
          try {
            const r = await api<ReceiptResponse>(`/api/receipt/${receipt}`)
            // answered_by_sop replies are played immediately at the machine, not kept here.
            if (r.answered_by_sop || !r.text || !r.ack_audio_key) return null
            return { receipt, text: r.text, audio_key: r.ack_audio_key, responded_at: r.responded_at }
          } catch {
            return null
          }
        }),
      )
      if (!cancelled) setAnswers(settled.filter((a): a is Answer => a !== null))
    }
    void load()
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [machineId])

  if (!answers.length) return null

  return (
    <section className="mb-5 overflow-hidden rounded-3xl border-2 border-primary bg-primary-light shadow-sm">
      <div className="flex items-center gap-3 px-4 pt-4">
        <Ticket size={22} className="shrink-0 text-primary-dark" />
        <span className="text-lg font-semibold text-primary-dark">{WORDS.title}</span>
      </div>
      <ul className="mt-3">
        {answers.map((answer) => (
          <li key={answer.receipt} className="flex items-start gap-3 border-t border-primary/30 p-4">
            <div className="flex-1">
              <p className="text-lg leading-snug text-ink" dir="auto">
                {answer.text}
              </p>
              {answer.responded_at && (
                <p className="mt-1 text-xs text-ink-faint">
                  {new Date(answer.responded_at).toLocaleString(undefined, {
                    day: 'numeric',
                    month: 'short',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </p>
              )}
            </div>
            <button
              onClick={() => new Audio(`/api/audio/${answer.audio_key}`).play().catch(() => {})}
              aria-label={WORDS.play}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-ink bg-white text-ink transition-colors hover:bg-ink hover:text-white"
            >
              <Play size={20} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
