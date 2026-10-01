import { useEffect, useRef } from 'react'

const BAR_COUNT = 28

/** Live amplitude bars driven by the mic's own audio data while recording. */
export function Waveform({ stream, active }: { stream: MediaStream | null; active: boolean }) {
  const barsRef = useRef<HTMLDivElement[]>([])

  useEffect(() => {
    if (!stream || !active) return
    const AudioContextCtor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    const ctx = new AudioContextCtor()
    const source = ctx.createMediaStreamSource(stream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 64
    analyser.smoothingTimeConstant = 0.7
    source.connect(analyser)
    const data = new Uint8Array(analyser.frequencyBinCount)

    let raf = 0
    const tick = () => {
      analyser.getByteFrequencyData(data)
      const step = Math.floor(data.length / BAR_COUNT) || 1
      barsRef.current.forEach((bar, i) => {
        if (!bar) return
        const v = data[i * step] ?? 0
        bar.style.transform = `scaleY(${Math.max(0.08, v / 255)})`
      })
      raf = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      source.disconnect()
      ctx.close().catch(() => {})
    }
  }, [stream, active])

  return (
    <div className="flex h-10 items-center gap-[3px]" aria-hidden="true">
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => {
            if (el) barsRef.current[i] = el
          }}
          className="h-full w-[3px] origin-center rounded-full bg-white/70 transition-transform duration-75"
          style={{ transform: 'scaleY(0.08)' }}
        />
      ))}
    </div>
  )
}
