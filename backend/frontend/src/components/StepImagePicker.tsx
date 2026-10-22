import { Check, Image as ImageIcon, Loader2 } from 'lucide-react'
import { type ChangeEvent, useRef, useState } from 'react'
import { apiAuth } from '../lib/api'
import type { StoredSOP } from '../lib/types'

/** Upload (or replace) one step's illustration: ask the backend for a signed Storage URL, PUT
 * the file straight there, then tell the backend where it landed - same three-call shape as the
 * candidate-resume upload in pages/hr/Overview.tsx. */
export function StepImagePicker({ stepId, onUploaded }: { stepId: number; onUploaded: (sop: StoredSOP) => void }) {
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function onFileChosen(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const { upload_url, storage_path } = await apiAuth<{ upload_url: string; storage_path: string }>(
        `/api/sop/step/${stepId}/image-upload-url`,
        { method: 'POST' },
      )
      const uploadRes = await fetch(upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': file.type || 'application/octet-stream' },
        body: file,
      })
      if (!uploadRes.ok) throw new Error('Image upload failed')
      const sop = await apiAuth<StoredSOP>(`/api/sop/step/${stepId}/image`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storage_path }),
      })
      onUploaded(sop)
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add that image.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <label
        className={`inline-flex cursor-pointer items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all hover:-translate-y-0.5 ${
          done ? 'border-safe/40 bg-safe-bg text-safe' : 'border-border-strong bg-white text-ink hover:border-ink-soft'
        }`}
      >
        {busy ? <Loader2 size={14} className="animate-spin" /> : done ? <Check size={14} /> : <ImageIcon size={14} />}
        {busy ? 'Uploading...' : done ? 'Image added' : 'Add image'}
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={onFileChosen} disabled={busy} />
      </label>
      {error && <span className="text-xs font-medium text-stop">{error}</span>}
    </div>
  )
}
