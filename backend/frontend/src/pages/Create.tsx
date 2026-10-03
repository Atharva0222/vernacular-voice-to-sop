import { motion } from 'framer-motion'
import { ChevronRight, Mic, Square, Upload, Wand2 } from 'lucide-react'
import { type ChangeEvent, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { BackLink, PageHeader } from '../components/layout'
import { Button, Select, Spinner } from '../components/ui'
import { apiAuth, getMachine } from '../lib/api'
import { useRequireRole } from '../hooks/useSession'
import type { Language, MachineSummary, Step, StoredSOP } from '../lib/types'

const LANG_LABEL: Record<string, string> = { hi: 'Hindi', mr: 'Marathi' }

export default function Create() {
  const staff = useRequireRole('supervisor')
  const [params] = useSearchParams()
  const machineId = params.get('machine')

  const [machine, setMachine] = useState<MachineSummary | null>(null)
  const [currentSop, setCurrentSop] = useState<StoredSOP | null>(null)
  const [showRecorder, setShowRecorder] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [lang, setLang] = useState<'auto' | Language>('auto')
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioLabel, setAudioLabel] = useState('')
  const [stage, setStage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [detectedLang, setDetectedLang] = useState<Language | null>(null)
  const [generating, setGenerating] = useState(false)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])

  useEffect(() => {
    if (!staff || !machineId) return
    let cancelled = false
    async function load() {
      try {
        const m = await getMachine(machineId!)
        if (cancelled) return
        setMachine(m)
        if (m.sop_id) {
          const sop = await apiAuth<StoredSOP>(`/api/machine/${m.id}/sop`)
          if (cancelled) return
          setCurrentSop(sop)
        } else {
          setShowRecorder(true)
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Could not load this machine.')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [staff, machineId])

  async function toggleRecord() {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        chunksRef.current = []
        const recorder = new MediaRecorder(stream)
        recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
        recorder.onstop = () => {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          setAudioBlob(blob)
          setAudioLabel(`Recorded ${(blob.size / 1024).toFixed(0)} KB`)
          stream.getTracks().forEach((t) => t.stop())
        }
        recorder.start()
        recorderRef.current = recorder
        setIsRecording(true)
      } catch (err) {
        setError('The microphone is blocked or unavailable: ' + (err instanceof Error ? err.message : String(err)))
      }
    } else {
      recorderRef.current?.stop()
      setIsRecording(false)
    }
  }

  function onFileChosen(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) {
      setAudioBlob(file)
      setAudioLabel(file.name)
    }
  }

  async function generate() {
    if (!audioBlob || !machineId) return
    setError(null)
    setGenerating(true)
    try {
      setStage('Listening to the recording...')
      const form = new FormData()
      form.append('audio', audioBlob, 'clip.webm')
      form.append('language', lang)
      const { transcript: text, detected_language } = await apiAuth<{ transcript: string; detected_language: Language }>(
        '/api/transcribe',
        { method: 'POST', body: form },
      )
      setTranscript(text)
      setDetectedLang(detected_language)

      setStage('Splitting it into steps...')
      const { steps } = await apiAuth<{ steps: Step[] }>('/api/structure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: text, language: detected_language }),
      })

      setStage(`Saving ${steps.length} cards...`)
      const sop = await apiAuth<StoredSOP>('/api/sop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          machine_id: Number(machineId),
          title: steps[0]?.text.slice(0, 60) || 'SOP',
          language: detected_language,
          transcript: text,
          steps,
        }),
      })
      window.location.hash = `#/cards?machine=${sop.machine_id}`
    } catch (err) {
      setStage(null)
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setGenerating(false)
    }
  }

  if (!staff) return null

  if (!machineId) {
    return (
      <AppShell role={staff.role} name={staff.name}>
        <BackLink to="/machines">Machines</BackLink>
        <p className="rounded-2xl bg-stop-bg px-4 py-3 text-sm font-medium text-stop">
          No machine chosen. Go back and pick one.
        </p>
      </AppShell>
    )
  }

  return (
    <AppShell role={staff.role} name={staff.name}>
      <BackLink to="/machines">Machines</BackLink>

      <PageHeader
        title={machine?.name ?? ' '}
        subtitle="Say the steps out loud, one sentence each, in Hindi or Marathi. They become the cards the worker at this machine sees and hears."
        right={
          machine && (
            <div className="flex gap-2">
              <span className="inline-flex items-center rounded-full bg-ink px-3 py-1 text-xs font-semibold text-white">
                {machine.line_name}
              </span>
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  machine.sop_id ? 'bg-safe-bg text-safe' : 'bg-caution-bg text-caution'
                }`}
              >
                {machine.sop_id ? `${machine.step_count} cards in use` : 'No cards yet'}
              </span>
            </div>
          )
        }
      />

      {loadError && <p className="rounded-2xl bg-stop-bg px-4 py-3 text-sm font-medium text-stop">{loadError}</p>}

      {currentSop && !showRecorder && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-border bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-bold text-ink">Cards now in use, version {currentSop.version}</h2>
            <a href={`#/cards?machine=${machine?.id}`} className="flex items-center text-sm font-semibold text-primary-dark hover:underline">
              Open the worker's cards <ChevronRight size={15} />
            </a>
          </div>
          <ol className="flex flex-col gap-2.5">
            {currentSop.steps.map((s) => (
              <li key={s.id} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-canvas text-xs font-bold tabular-nums text-ink-soft">
                  {s.step_number}
                </span>
                <span className="lang-dev text-base leading-snug text-ink" dir="auto">
                  {s.text}
                </span>
              </li>
            ))}
          </ol>
          <Button variant="secondary" className="mt-5 w-full" onClick={() => setShowRecorder(true)}>
            <Mic size={16} /> Record a new version
          </Button>
        </motion.div>
      )}

      {showRecorder && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="rounded-3xl border border-border bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium text-ink-soft" htmlFor="lang">
              Spoken in
            </label>
            <Select id="lang" value={lang} onChange={(e) => setLang(e.target.value as 'auto' | Language)}>
              <option value="auto">Detect the language</option>
              <option value="hi">Hindi</option>
              <option value="mr">Marathi</option>
            </Select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant={isRecording ? 'danger' : 'primary'} onClick={toggleRecord}>
              {isRecording ? <Square size={16} /> : <Mic size={16} />}
              {isRecording ? 'Stop recording' : 'Start recording'}
            </Button>
            <span className="text-sm text-ink-faint">or</span>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-border-strong bg-white px-5 py-2.5 text-sm font-semibold text-ink transition-all hover:-translate-y-0.5 hover:border-ink-soft">
              <Upload size={16} /> Upload a clip
              <input type="file" accept="audio/*" className="hidden" onChange={onFileChosen} />
            </label>
            {audioLabel && <span className="text-sm text-ink-soft">{audioLabel}</span>}
          </div>

          <Button className="mt-5 w-full" disabled={!audioBlob} loading={generating} onClick={generate}>
            <Wand2 size={16} /> Make the cards
          </Button>

          {stage && (
            <p className="mt-4 flex items-center gap-2 text-sm text-ink-soft">
              <Spinner size={14} /> {stage}
            </p>
          )}
          {error && <p className="mt-4 rounded-xl bg-stop-bg px-3 py-2 text-sm font-medium text-stop">{error}</p>}

          {transcript && (
            <details className="mt-4 rounded-xl bg-canvas p-3">
              <summary className="cursor-pointer text-sm font-medium text-ink-soft">
                What was heard
                {detectedLang && (
                  <span className="ml-2 inline-flex items-center rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-ink-soft">
                    {LANG_LABEL[detectedLang] ?? detectedLang}
                  </span>
                )}
              </summary>
              <p className="lang-dev mt-2 text-base text-ink" dir="auto">
                {transcript}
              </p>
            </details>
          )}
        </motion.div>
      )}
    </AppShell>
  )
}
