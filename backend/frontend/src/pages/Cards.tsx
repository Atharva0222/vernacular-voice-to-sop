import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Mic, Play, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BackLink, Shell } from '../components/layout'
import { EmptyState, Spinner } from '../components/ui'
import { Waveform } from '../components/Waveform'
import { api, getMachine } from '../lib/api'
import { iconFor } from '../lib/icons'
import type { MachineSummary, StoredSOP, StoredStep } from '../lib/types'

const POLL_MS = 10000

const WORDS = {
  loading: (n: number) => `${n} कार्ड की आवाज़ तैयार हो रही है...`,
  safety: 'सुरक्षा चेतावनी',
  hold: 'बोलने के लिए दबाकर रखें',
  listening: 'सुन रहे हैं...',
  heard: 'सुन लिया गया — कार्ड से मिलाया जा रहा है...',
  fromSop: 'कार्ड में इसका जवाब है — सुनने के लिए दबाएं',
  toManager: 'मैनेजर को भेज दिया गया है',
  reply: 'मैनेजर का जवाब आया है — सुनने के लिए दबाएं',
  unclear: 'आवाज़ समझ नहीं आई। कृपया फिर से बोलें।',
  noMachine: 'कोई मशीन नहीं चुनी गई। पीछे जाकर मशीन चुनें।',
  noCards: 'इस मशीन के लिए अभी कोई कार्ड नहीं है।',
  noCardsSub: 'अपने सुपरवाइज़र से कहें कि वे इसका तरीका रिकॉर्ड करें।',
  pickAnother: 'दूसरी मशीन चुनें',
}

type Step = StoredStep & { audio_url: string | null }

export default function Cards() {
  const [params] = useSearchParams()
  const machineId = params.get('machine')

  const [machine, setMachine] = useState<MachineSummary | null>(null)
  const [sop, setSop] = useState<StoredSOP | null>(null)
  const [steps, setSteps] = useState<Step[] | null>(null)
  const [stage, setStage] = useState<string | null>('कार्ड आ रहे हैं...')
  const [error, setError] = useState<string | null>(null)
  const [empty, setEmpty] = useState(false)

  const [recording, setRecording] = useState(false)
  const [speakLabel, setSpeakLabel] = useState(WORDS.hold)
  const [speakHint, setSpeakHint] = useState('जो गड़बड़ है वह बताएं, या मशीन के बारे में पूछें।')
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [answer, setAnswer] = useState<{ audio: HTMLAudioElement } | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const heldRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!machineId) {
        setStage(null)
        setError(WORDS.noMachine)
        return
      }
      try {
        const m = await getMachine(machineId)
        if (cancelled) return
        setMachine(m)
        if (!m.sop_id) {
          setStage(null)
          setEmpty(true)
          return
        }
        const fullSop = await api<StoredSOP>(`/api/machine/${machineId}/sop`)
        if (cancelled) return
        setSop(fullSop)
        setStage(WORDS.loading(fullSop.steps.length))

        const withAudio: Step[] = []
        for (const step of fullSop.steps) {
          const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: step.text, language: fullSop.language }),
          })
          withAudio.push({ ...step, audio_url: res.ok ? ((await res.json()) as { audio_url: string }).audio_url : null })
        }
        if (cancelled) return
        setSteps(withAudio)
        setStage(null)
      } catch (err) {
        if (cancelled) return
        setStage(null)
        setError(err instanceof Error ? err.message : 'Something went wrong.')
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [machineId])

  async function pollAnswer(receipt: string) {
    const report = await api<{
      status: string
      ack_audio_key: string | null
      answered_by_sop: boolean
    }>(`/api/receipt/${receipt}`)

    if (report.status === 'failed') {
      setSpeakHint(WORDS.unclear)
      return
    }
    if (report.status === 'received') {
      setTimeout(() => pollAnswer(receipt), POLL_MS)
      return
    }
    if (report.answered_by_sop) {
      if (report.ack_audio_key) playAnswer(report.ack_audio_key, WORDS.fromSop)
      return
    }
    if (report.ack_audio_key) {
      playAnswer(report.ack_audio_key, WORDS.reply)
      return
    }
    setSpeakHint(WORDS.toManager)
    setTimeout(() => pollAnswer(receipt), POLL_MS)
  }

  function playAnswer(audioKey: string, message: string) {
    const audio = new Audio(`/api/audio/${audioKey}`)
    setSpeakHint(message)
    setAnswer({ audio })
    audio.play().catch(() => {})
  }

  async function startRecording() {
    if (!sop) return
    heldRef.current = true
    setAnswer(null)
    const media = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (!heldRef.current) {
      media.getTracks().forEach((t) => t.stop())
      return
    }
    setStream(media)
    const parts: BlobPart[] = []
    const recorder = new MediaRecorder(media)
    recorder.ondataavailable = (e) => parts.push(e.data)
    recorder.onstop = async () => {
      media.getTracks().forEach((t) => t.stop())
      setStream(null)
      setRecording(false)
      setSpeakLabel(WORDS.hold)

      const form = new FormData()
      form.append('audio', new Blob(parts, { type: 'audio/webm' }), 'question.webm')
      form.append('sop_id', String(sop.id))
      form.append('language', sop.language)
      try {
        const created = await api<{ receipt: string }>('/api/ask', { method: 'POST', body: form })
        setSpeakHint(WORDS.heard)
        pollAnswer(created.receipt)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Could not send the recording.')
      }
    }
    recorder.start()
    recorderRef.current = recorder
    setRecording(true)
    setSpeakLabel(WORDS.listening)
  }

  function stopRecording() {
    heldRef.current = false
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  return (
    <div className="lang-dev">
      <Shell>
        <div className="pb-36">
          <BackLink to="/machines">मशीनें</BackLink>

          <header className="mb-8">
            <h1 className="min-h-[1.2em] text-4xl font-extrabold tracking-tight text-ink">
              {machine?.name ?? ' '}
            </h1>
            {machine && (
              <span className="mt-3 inline-flex items-center rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white">
                {machine.line_name}
              </span>
            )}
          </header>

          {stage && (
            <p className="mb-6 flex items-center gap-2 text-lg text-ink-soft">
              <Spinner /> {stage}
            </p>
          )}

          {error && <p className="mb-6 rounded-2xl bg-stop-bg px-4 py-3 text-base font-medium text-stop">{error}</p>}

          {empty && (
            <EmptyState
              title={WORDS.noCards}
              subtitle={WORDS.noCardsSub}
              action={
                <a href="#/machines" className="mt-2 text-sm font-semibold text-primary-dark">
                  {WORDS.pickAnother}
                </a>
              }
            />
          )}

          {steps && (
            <div className="flex flex-col gap-4">
              {steps.map((step, i) => {
                const Icon = iconFor(step)
                return (
                  <motion.article
                    key={step.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`flex items-stretch overflow-hidden rounded-3xl border bg-white shadow-sm ${
                      step.is_safety_warning ? 'border-caution/40' : 'border-border'
                    }`}
                  >
                    <div
                      className={`flex w-16 shrink-0 items-center justify-center text-2xl font-bold tabular-nums text-white ${
                        step.is_safety_warning ? 'bg-caution' : 'bg-ink'
                      }`}
                    >
                      {step.step_number}
                    </div>
                    <div className="flex flex-1 items-start gap-4 p-5">
                      <Icon size={26} className="mt-0.5 shrink-0 text-ink-soft" />
                      <div className="flex-1">
                        <p className="text-xl leading-snug text-ink" dir="auto">
                          {step.text}
                        </p>
                        {step.is_safety_warning && (
                          <span className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-caution">
                            <AlertTriangle size={16} /> {WORDS.safety}
                          </span>
                        )}
                      </div>
                      {step.audio_url && (
                        <button
                          onClick={() => new Audio(step.audio_url!).play()}
                          aria-label="सुनें"
                          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 border-ink text-ink transition-colors hover:bg-ink hover:text-white"
                        >
                          <Play size={20} />
                        </button>
                      )}
                    </div>
                  </motion.article>
                )
              })}
            </div>
          )}
        </div>

        {sop && (
          <div className="fixed inset-x-0 bottom-0 z-10 border-t border-border bg-white/90 backdrop-blur-md">
            <div className="mx-auto flex max-w-3xl items-center gap-5 px-5 py-4 sm:px-8">
              <button
                onPointerDown={startRecording}
                onPointerUp={stopRecording}
                onPointerLeave={stopRecording}
                title={WORDS.hold}
                aria-label={WORDS.hold}
                className={`relative flex h-20 w-20 shrink-0 touch-none select-none items-center justify-center rounded-full text-white shadow-lg transition-transform active:scale-95 ${
                  recording ? 'bg-rose-500' : 'bg-gradient-to-br from-stop to-rose-600'
                }`}
              >
                {recording && (
                  <motion.span
                    className="absolute inset-0 rounded-full bg-rose-400"
                    animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                    transition={{ duration: 1.2, repeat: Infinity, ease: 'easeOut' }}
                  />
                )}
                <Mic size={32} className="relative" />
              </button>

              <div className="min-w-0 flex-1">
                <AnimatePresence mode="popLayout">
                  {recording ? (
                    <motion.div
                      key="wave"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex h-10 items-center rounded-xl bg-ink px-3"
                    >
                      <Waveform stream={stream} active={recording} />
                    </motion.div>
                  ) : (
                    <motion.div key="text" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      <strong className="block text-lg font-bold text-ink">{speakLabel}</strong>
                      <span className="text-sm text-ink-soft" dir="auto">
                        {speakHint}
                      </span>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {answer && (
                <button
                  onClick={() => answer.audio.play()}
                  title="जवाब सुनें"
                  aria-label="जवाब सुनें"
                  className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-safe to-emerald-600 text-white shadow-md"
                >
                  <Volume2 size={24} />
                </button>
              )}
            </div>
          </div>
        )}
      </Shell>
    </div>
  )
}
